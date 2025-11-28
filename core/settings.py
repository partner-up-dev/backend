"""Application Settings - All configuration from environment variables.

Settings are organized by domain using nested models.
Environment variables use nested delimiter '__' to map to nested fields.
Example: DATABASE__URL maps to settings.database.url

The default env file location is /run/secrets/.env for production deployments.
This can be overridden by setting the ENV_FILE environment variable.
For development, create a .env file in the project root and set ENV_FILE=.env
"""

import os
from functools import lru_cache
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default env file path - can be overridden by ENV_FILE environment variable
_ENV_FILE = os.getenv("ENV_FILE", "/run/secrets/.env")


class DatabaseSettings(BaseModel):
    """Database configuration."""
    url: str = ""


class RedisSettings(BaseModel):
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0


class AuthSettings(BaseModel):
    """Authentication / JWT configuration."""
    jwt_secret_key: str = ""
    jwt_algorithms: list[str] = ["HS256"]
    jwt_allowed_audiences: tuple[str, ...] = ("authenticated", "anon", "service_role")


class HttpSettings(BaseModel):
    """HTTP Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    real_host: str = "localhost"


class SupabaseSettings(BaseModel):
    """Supabase configuration."""
    url: str = ""
    serv_key: str = ""
    anon_key: str = ""


class WeixinSettings(BaseModel):
    """WeChat configuration.

    The partner_up_wxmp_appid has a default value for backwards compatibility,
    but should be set via environment variables for different environments.
    """
    partner_up_wxmp_appid: str = ""
    partner_up_wxmp_secret: str = ""
    partner_up_wxsa_appid: str = ""
    partner_up_wxsa_secret: str = ""


class WechatPaySettings(BaseModel):
    """WeChat Pay configuration."""
    mchid: str = ""
    pri_key_path: str = ""
    serial_no: str = ""
    api_v3_key: str = ""
    sign_type: str = "RSA"
    cert_dir: str = ""


class LbsSettings(BaseModel):
    """Location-Based Services configuration."""
    apikey: str = ""


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Settings are organized by domain using nested models.
    Environment variables use nested delimiter '__' to map to nested fields.

    Examples:
        DATABASE__URL -> settings.database.url
        REDIS__HOST -> settings.redis.host
        AUTH__JWT_SECRET_KEY -> settings.auth.jwt_secret_key

    The env file location defaults to /run/secrets/.env but can be overridden
    by setting the ENV_FILE environment variable.
    """

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Environment
    env: str = "development"

    # Nested settings by domain
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    auth: AuthSettings = AuthSettings()
    http: HttpSettings = HttpSettings()
    supabase: SupabaseSettings = SupabaseSettings()
    weixin: WeixinSettings = WeixinSettings()
    wechat_pay: WechatPaySettings = WechatPaySettings()
    lbs: LbsSettings = LbsSettings()

    # Backwards compatibility properties
    @property
    def database_url(self) -> str:
        """Backwards compatible database URL."""
        return self.database.url

    @property
    def redis_host(self) -> str:
        """Backwards compatible redis host."""
        return self.redis.host

    @property
    def redis_port(self) -> int:
        """Backwards compatible redis port."""
        return self.redis.port

    @property
    def redis_password(self) -> str:
        """Backwards compatible redis password."""
        return self.redis.password

    @property
    def redis_db(self) -> int:
        """Backwards compatible redis db."""
        return self.redis.db

    @property
    def jwt_secret_key(self) -> str:
        """Backwards compatible JWT secret key."""
        return self.auth.jwt_secret_key

    @property
    def jwt_algorithms(self) -> list[str]:
        """Backwards compatible JWT algorithms."""
        return self.auth.jwt_algorithms

    @property
    def jwt_allowed_audiences(self) -> tuple[str, ...]:
        """Backwards compatible JWT allowed audiences."""
        return self.auth.jwt_allowed_audiences

    @property
    def http_host(self) -> str:
        """Backwards compatible HTTP host."""
        return self.http.host

    @property
    def http_port(self) -> int:
        """Backwards compatible HTTP port."""
        return self.http.port

    @property
    def http_real_host(self) -> str:
        """Backwards compatible HTTP real host."""
        return self.http.real_host

    @property
    def supabase_url(self) -> str:
        """Backwards compatible Supabase URL."""
        return self.supabase.url

    @property
    def supabase_serv_key(self) -> str:
        """Backwards compatible Supabase service key."""
        return self.supabase.serv_key

    @property
    def supabase_anon_key(self) -> str:
        """Backwards compatible Supabase anon key."""
        return self.supabase.anon_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
