from dataclasses import dataclass, field
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Settings:
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", "127.0.0.1"))
    db_port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", "root"))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", "task_api"))

    redis_host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "127.0.0.1"))
    redis_port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    redis_db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cache_ttl: int = 60

    @property
    def database_url(self) -> str:
        return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
