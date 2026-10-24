from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（.env 统一配置文件位于此处）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # 服务器地址：本机局域网 IP，仅用于启动时打印访问提示（换网络只需改这一项）
    SERVER_IP: str = "192.168.1.7"
    # 后端服务
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8001
    # 主前端（班主任端）
    FRONTEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 3000
    # 家长端前端
    PARENT_HOST: str = "0.0.0.0"
    PARENT_PORT: int = 5174
    # 数据库 / 安全
    # 默认 SQLite（零依赖快速体验）；生产建议 PostgreSQL：
    #   postgresql://ddclass_user:密码@127.0.0.1:5432/ddclass
    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'ddclass.db').as_posix()}"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    # 额外允许的 CORS 来源（逗号分隔），默认已包含 SERVER_IP/localhost 下两个前端端口，
    # 仅在浏览器直连后端（绕过前端代理）时才需要追加，如 https://xxx.cpolar.io
    CORS_ORIGINS: str = ""
    # 公网访问（cpolar 内网穿透，临时远程测试用）
    PUBLIC_ACCESS: bool = False
    CPOLAR_AUTHTOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # 绝对路径：与启动时所在目录无关
        env_file_encoding="utf-8",
    )


settings = Settings()

# 已知弱密钥（config 默认值与 .env.example 模板值）：命中则拒绝启动，
# 防止 .env 缺失/未改时用公开默认值签发 JWT（任何人可伪造登录令牌）
_WEAK_SECRET_KEYS = {
    "",
    "your-super-secret-key-change-in-production",
    "change-me-to-a-long-random-string",
    "change-me",
    "secret",
}

if settings.SECRET_KEY.strip().lower() in _WEAK_SECRET_KEYS:
    import secrets as _secrets
    import sys

    print(
        "[config] 错误: SECRET_KEY 未配置或仍为模板默认值，为安全起见拒绝启动。\n"
        "[config] 请编辑项目根目录 .env，将 SECRET_KEY 改为随机长字符串，例如：\n"
        f"[config]   SECRET_KEY={_secrets.token_hex(32)}\n"
        "[config] （上面这行是本机刚生成的随机密钥，可直接复制粘贴）",
        file=sys.stderr,
    )
    raise SystemExit(1)
