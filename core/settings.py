"""Application Settings - All configuration from environment variables."""

import os
from functools import lru_cache
from typing import Optional as Opt
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    env: str = "development"

    # Database
    database_url: str = ""

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # Auth / JWT
    jwt_secret_key: str = ""
    jwt_algorithms: list[str] = ["HS256"]
    jwt_allowed_audiences: tuple[str, ...] = ("authenticated", "anon", "service_role")

    # Transport / Server
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    http_real_host: str = "localhost"

    # Supabase
    supabase_url: str = ""
    supabase_serv_key: str = ""
    supabase_anon_key: str = ""

    # WeChat
    weixin_partner_up_wxmp_appid: str = "wx7674f72ff1eb49e6"
    weixin_partner_up_wxmp_secret: str = ""
    weixin_partner_up_wxsa_appid: str = ""
    weixin_partner_up_wxsa_secret: str = ""

    # WeChat Pay
    wechat_pay_mchid: str = ""
    wechat_pay_pri_key_path: str = ""
    wechat_pay_serial_no: str = ""
    wechat_pay_api_v3_key: str = ""
    wechat_pay_sign_type: str = "RSA"
    wechat_pay_cert_dir: str = ""

    # LBS
    lbs_apikey: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
