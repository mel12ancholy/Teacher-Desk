"""接口限流中间件（内存实现，单进程部署有效）

两套限流器，共用同一滑动窗口实现：

1. 家长端限流（ParentRateLimitMiddleware → GET /api/parent/*）
   背景：家长端接口不需要登录，仅凭 8 位家长码即可查询学生成绩等隐私数据，
   若无限制可被脚本暴力枚举。两层防护：
   - 按客户端限流：每分钟请求上限 + 连续校验失败达到阈值后封禁该客户端一段时间
   - 全局失败预算：正常家长持有效码，几乎不产生校验失败；爆破者的每次错误猜测
     都消耗全局预算，超限后暂停所有家长端查询一分钟（不依赖客户端 IP 可识别性，
     即使所有请求都经同一代理转发也依然有效）
   失败判定：接口返回 404/403（家长码无效/过期），或 /verify/ 返回 200 但
   valid=false（verify 对无效码也返回 200，需读取响应体判断）。

2. 登录限流（LoginRateLimitMiddleware → POST /api/auth/login）
   防止对登录接口的密码暴力猜测：单客户端失败次数阈值 + 封禁 + 全局失败预算。
   失败判定：响应 401（用户名或密码错误）；登录成功清空该客户端失败计数。

客户端识别：优先取 X-Forwarded-For（前端 Vite 代理已开启 xfwd 转发真实 IP），
取不到时退回连接对端地址。

注意：状态保存在进程内存中，重启清零；多进程部署（如 gunicorn 多 worker）时
各进程独立计数，阈值应按进程数相应放宽。
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

# ==================== 家长端参数 ====================
# 单客户端：每分钟请求上限
PARENT_MAX_REQUESTS_PER_MINUTE = 60
# 单客户端：15 分钟内校验失败达到该次数则封禁 15 分钟
PARENT_FAILURE_LIMIT = 20
# 兼容旧名（tests 中引用）
CLIENT_FAILURE_LIMIT = PARENT_FAILURE_LIMIT
# 全局：每分钟校验失败达到该次数，所有家长端查询暂停一分钟
PARENT_GLOBAL_FAILURE_LIMIT_PER_MINUTE = 40

# ==================== 登录参数 ====================
# 单客户端：每分钟登录尝试上限（正常人工登录远低于此）
LOGIN_MAX_REQUESTS_PER_MINUTE = 20
# 单客户端：15 分钟内登录失败达到该次数则封禁 15 分钟
LOGIN_FAILURE_LIMIT = 8
# 全局：每分钟登录失败达到该次数，登录暂停一分钟（防代理后共享 IP 的爆破）
LOGIN_GLOBAL_FAILURE_LIMIT_PER_MINUTE = 30

_BLOCK_SECONDS = 15 * 60
_REQUEST_WINDOW = 60


def _prune(bucket: deque, now: float, window: float) -> None:
    while bucket and bucket[0] <= now - window:
        bucket.popleft()


class SlidingWindowLimiter:
    """通用滑动窗口限流器：请求配额 + 客户端失败封禁 + 可选全局失败预算（线程安全）"""

    def __init__(
        self,
        max_requests_per_minute: int,
        failure_limit: int,
        block_seconds: int = _BLOCK_SECONDS,
        global_failure_limit_per_minute: int | None = None,
        quota_message: str = "请求过于频繁，请稍后再试",
        blocked_message: str = "操作失败次数过多，请稍后再试",
        global_message: str = "当前访问过于频繁，请一分钟后再试",
    ) -> None:
        self.max_requests = max_requests_per_minute
        self.failure_limit = failure_limit
        self.block_seconds = block_seconds
        self.global_failure_limit = global_failure_limit_per_minute
        self.quota_message = quota_message
        self.blocked_message = blocked_message
        self.global_message = global_message

        self._lock = threading.Lock()
        self._requests: dict[str, deque] = defaultdict(deque)
        self._client_failures: dict[str, deque] = defaultdict(deque)
        self._global_failures: deque = deque()

    def clear(self) -> None:
        """清空全部计数（测试用）"""
        with self._lock:
            self._requests.clear()
            self._client_failures.clear()
            self._global_failures.clear()

    @staticmethod
    def client_key(request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request) -> "tuple[bool, int, str]":
        """请求前检查。返回 (是否放行, Retry-After 秒, 拒绝原因)"""
        key = self.client_key(request)
        now = time.monotonic()
        with self._lock:
            failures = self._client_failures[key]
            _prune(failures, now, self.block_seconds)
            if len(failures) >= self.failure_limit:
                retry_after = max(1, int(failures[0] + self.block_seconds - now) + 1)
                return False, retry_after, self.blocked_message

            if self.global_failure_limit is not None:
                _prune(self._global_failures, now, _REQUEST_WINDOW)
                if len(self._global_failures) >= self.global_failure_limit:
                    retry_after = max(1, int(self._global_failures[0] + _REQUEST_WINDOW - now) + 1)
                    return False, retry_after, self.global_message

            requests = self._requests[key]
            _prune(requests, now, _REQUEST_WINDOW)
            if len(requests) >= self.max_requests:
                retry_after = max(1, int(requests[0] + _REQUEST_WINDOW - now) + 1)
                return False, retry_after, self.quota_message
            requests.append(now)
            return True, 0, ""

    def record_failure(self, request) -> None:
        """记一次失败（客户端维度 + 全局预算）"""
        key = self.client_key(request)
        now = time.monotonic()
        with self._lock:
            self._client_failures[key].append(now)
            self._global_failures.append(now)

    def record_success(self, request) -> None:
        """成功：清掉该客户端的历史失败，避免合法用户被误伤"""
        with self._lock:
            self._client_failures.pop(self.client_key(request), None)


# 全局共享实例（run.py 单进程部署；测试中可直接 clear 重置）
parent_limiter = SlidingWindowLimiter(
    max_requests_per_minute=PARENT_MAX_REQUESTS_PER_MINUTE,
    failure_limit=PARENT_FAILURE_LIMIT,
    block_seconds=_BLOCK_SECONDS,
    global_failure_limit_per_minute=PARENT_GLOBAL_FAILURE_LIMIT_PER_MINUTE,
    blocked_message="家长码校验失败次数过多，请稍后再试",
    global_message="当前家长端访问过于频繁，请一分钟后再试",
)
# 兼容旧引用名
limiter = parent_limiter

login_limiter = SlidingWindowLimiter(
    max_requests_per_minute=LOGIN_MAX_REQUESTS_PER_MINUTE,
    failure_limit=LOGIN_FAILURE_LIMIT,
    block_seconds=_BLOCK_SECONDS,
    global_failure_limit_per_minute=LOGIN_GLOBAL_FAILURE_LIMIT_PER_MINUTE,
    blocked_message="登录失败次数过多，请 15 分钟后再试",
    global_message="登录尝试过于频繁，请一分钟后再试",
)


def _too_many_requests(retry_after: int, reason: str) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": reason},
        headers={"Retry-After": str(retry_after)},
    )


class ParentRateLimitMiddleware(BaseHTTPMiddleware):
    """挂在 /api/parent/* GET 查询接口上的限流中间件。

    家长码管理接口（POST generate-code / batch-generate-codes、DELETE revoke-code）
    需要 JWT 登录且为非 GET，不在限流范围内。
    """

    def __init__(self, app, limiter_instance: SlidingWindowLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter_instance or parent_limiter

    async def dispatch(self, request, call_next):
        if request.method != "GET" or not request.url.path.startswith("/api/parent/"):
            return await call_next(request)

        allowed, retry_after, reason = self.limiter.check(request)
        if not allowed:
            return _too_many_requests(retry_after, reason)

        response = await call_next(request)
        status = response.status_code

        if status == 200 and "/verify/" in request.url.path:
            # verify 对无效码返回 200 + {"valid": false}，需要读响应体才能判定失败；
            # 读完后用原 body/头重建响应继续向下传递
            body = b""
            async for chunk in response.body_iterator:
                body += chunk if isinstance(chunk, bytes) else chunk.encode("utf-8")
            response = Response(
                content=body,
                status_code=status,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
            try:
                invalid_verify = json.loads(body).get("valid") is False
            except Exception:
                invalid_verify = False
            if invalid_verify:
                self.limiter.record_failure(request)
            return response

        if status in (404, 403):
            self.limiter.record_failure(request)
        elif status == 200:
            self.limiter.record_success(request)
        return response


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """挂在 POST /api/auth/login 上的限流中间件：防密码暴力猜测。

    401 = 登录失败计入失败数；200 = 登录成功并清空该客户端失败计数。
    """

    def __init__(self, app, limiter_instance: SlidingWindowLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter_instance or login_limiter

    async def dispatch(self, request, call_next):
        if request.method != "POST" or request.url.path != "/api/auth/login":
            return await call_next(request)

        allowed, retry_after, reason = self.limiter.check(request)
        if not allowed:
            return _too_many_requests(retry_after, reason)

        response = await call_next(request)
        if response.status_code == 401:
            self.limiter.record_failure(request)
        elif response.status_code == 200:
            self.limiter.record_success(request)
        return response
