"""Account Managers."""

__all__ = ["SupabaseAuth", "get_account_profile", "get_account_profile_simple"]

import typing
import structlog
from typing import Optional as Opt
from gotrue import AsyncGoTrueClient
from fastapi import HTTPException

from core.settings import get_settings
from ..schemas import (
    AccountConfig,
    BaseProfile,
    AccountRef,
    AccountProfileSimple,
)


logger = structlog.get_logger(__name__)


class SupabaseAuth:
    @classmethod
    def get_anon_client(cls) -> AsyncGoTrueClient:
        settings = get_settings()
        return AsyncGoTrueClient(
            url=settings.supabase_url + "/auth/v1",
            headers={
                "apiKey": settings.supabase_anon_key,
                "authorization": f"Bearer {settings.supabase_anon_key}",
            },
        )

    @classmethod
    def get_authenticated_client(cls, access_token: str) -> AsyncGoTrueClient:
        settings = get_settings()
        return AsyncGoTrueClient(
            url=settings.supabase_url + "/auth/v1",
            headers={
                "apiKey": settings.supabase_anon_key,
                "authorization": f"Bearer {access_token}",
            },
        )

    @classmethod
    def get_serv_client(cls) -> AsyncGoTrueClient:
        settings = get_settings()
        return AsyncGoTrueClient(
            url=settings.supabase_url + "/auth/v1",
            headers={
                "apiKey": settings.supabase_serv_key,
                "authorization": f"Bearer {settings.supabase_serv_key}",
            },
        )


def get_account_profile(db, account_id: AccountRef, requester_id: Opt[str] = None) -> BaseProfile:
    """Get account profile, with public filter if requester is not the owner."""
    profile = db.get(BaseProfile, account_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if requester_id and profile.id != requester_id:
        config = db.get(AccountConfig, account_id)
        if config:
            return config.filter_public(profile)

    return profile


def get_account_profile_simple(db, account_id: AccountRef) -> AccountProfileSimple:
    """Get simplified account profile."""
    profile = db.get(BaseProfile, account_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return AccountProfileSimple(
        id=profile.id,
        nickname=profile.nickname,
        avatar=profile.avatar,
    )
