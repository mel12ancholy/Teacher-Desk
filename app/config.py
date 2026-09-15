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
    DATABASE_URL: str = "postgresql://ddclass_user:your_password@127.0.0.1:5432/ddclass"
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    # 公网访问（cpolar 内网穿透，临时远程测试用）
    PUBLIC_ACCESS: bool = False
    CPOLAR_AUTHTOKEN: str = ""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),  # 绝对路径：与启动时所在目录无关
        env_file_encoding="utf-8",
    )


settings = Settings()
