"""家长端接口限流（内存实现，单进程部署有效）

背景：家长端接口（/api/parent/<动作>/<家长码>）不需要登录，仅凭 8 位家长码即可
查询学生成绩等隐私数据，若无限制可被脚本暴力枚举。

两层防护：
1. 按客户端限流：每分钟请求上限 + 连续校验失败达到阈值后封禁该客户端一段时间。
   客户端优先取 X-Forwarded-For（前端 Vite 代理已开启 xfwd 转发真实 IP），
   取不到时退回连接对端地址。
2. 全局失败预算：正常家长持有效码，几乎不产生校验失败；爆破者的每次错误猜测都
   消耗全局预算。每分钟全局失败总数超限后，暂停所有家长端查询一分钟。
   这一层不依赖客户端 IP 可识别性——即使所有请求都经同一代理转发也依然有效。

失败判定：接口返回 404/403（家长码无效/过期），或 /verify/ 返回 200 但
valid=false（verify 对无效码也返回 200，需读取响应体判断）。

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

# 单客户端：每分钟请求上限
MAX_REQUESTS_PER_MINUTE = 60
# 单客户端：15 分钟内校验失败达到该次数则封禁 15 分钟
CLIENT_FAILURE_LIMIT = 20
CLIENT_BLOCK_SECONDS = 15 * 60
# 全局：每分钟校验失败达到该次数，所有家长端查询暂停一分钟
GLOBAL_FAILURE_LIMIT_PER_MINUTE = 40

_REQUEST_WINDOW = 60


def _prune(bucket: deque, now: float, window: float) -> None:
    while bucket and bucket[0] <= now - window:
        bucket.popleft()


class ParentRateLimiter:
    """GET /api/parent/* 查询接口的限流器（线程安全）"""

    def __init__(self) -> None:
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

    def _client_key(self, request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request) -> "tuple[bool, int, str]":
        """请求前检查。返回 (是否放行, Retry-After 秒, 拒绝原因)"""
        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            failures = self._client_failures[key]
            _prune(failures, now, CLIENT_BLOCK_SECONDS)
            if len(failures) >= CLIENT_FAILURE_LIMIT:
                retry_after = max(1, int(failures[0] + CLIENT_BLOCK_SECONDS - now) + 1)
                return False, retry_after, "家长码校验失败次数过多，请稍后再试"

            _prune(self._global_failures, now, _REQUEST_WINDOW)
            if len(self._global_failures) >= GLOBAL_FAILURE_LIMIT_PER_MINUTE:
                retry_after = max(1, int(self._global_failures[0] + _REQUEST_WINDOW - now) + 1)
                return False, retry_after, "当前家长端访问过于频繁，请一分钟后再试"

            requests = self._requests[key]
            _prune(requests, now, _REQUEST_WINDOW)
            if len(requests) >= MAX_REQUESTS_PER_MINUTE:
                retry_after = max(1, int(requests[0] + _REQUEST_WINDOW - now) + 1)
                return False, retry_after, "请求过于频繁，请稍后再试"
            requests.append(now)
            return True, 0, ""

    def record_failure(self, request) -> None:
        """记一次校验失败（客户端维度 + 全局预算）"""
        key = self._client_key(request)
        now = time.monotonic()
        with self._lock:
            self._client_failures[key].append(now)
            self._global_failures.append(now)

    def record_success(self, request) -> None:
        """校验成功：清掉该客户端的历史失败，避免合法家长被误伤"""
        key = self._client_key(request)
        with self._lock:
            self._client_failures.pop(key, None)


# 全局共享实例（run.py 单进程部署；测试中可直接 clear 重置）
limiter = ParentRateLimiter()


class ParentRateLimitMiddleware(BaseHTTPMiddleware):
    """挂在 /api/parent/* GET 查询接口上的限流中间件。

    家长码管理接口（POST generate-code / batch-generate-codes、DELETE revoke-code）
    需要 JWT 登录且为非 GET，不在限流范围内。
    """

    def __init__(self, app, limiter_instance: ParentRateLimiter | None = None) -> None:
        super().__init__(app)
        self.limiter = limiter_instance or limiter

    async def dispatch(self, request, call_next):
        if request.method != "GET" or not request.url.path.startswith("/api/parent/"):
            return await call_next(request)

        allowed, retry_after, reason = self.limiter.check(request)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": reason},
                headers={"Retry-After": str(retry_after)},
            )

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
