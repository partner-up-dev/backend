"""Account App Routes.

Business logic endpoints for account management.
Simple CRUD operations (get, create, put, delete, upsert) are handled by direct
database access from the client.
"""

import fastapi
from fastapi import Depends, HTTPException

from core.auth import AuthInfo, require_auth
from core.engine import get_db_session
import sqlmodel

from .schemas import (
    BaseProfile,
    BaseProfileEditable,
    AccountConfig,
    GeoProfile,
)

router = fastapi.APIRouter()


@router.get("/profile/me")
def get_my_profile(
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> BaseProfile:
    """Get current user's profile."""
    profile = db.get(BaseProfile, auth.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/profile/me")
def update_my_profile(
    body: BaseProfileEditable,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> BaseProfile:
    """Update current user's profile.

    Only updates fields that are provided (partial update).
    """
    profile = db.get(BaseProfile, auth.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/config/me")
def get_my_config(
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> AccountConfig:
    """Get current user's config."""
    config = db.get(AccountConfig, auth.user_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.get("/geo/me")
def get_my_geo_profile(
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> GeoProfile:
    """Get current user's geo profile."""
    geo_profile = db.get(GeoProfile, auth.user_id)
    if not geo_profile:
        raise HTTPException(status_code=404, detail="Geo profile not found")
    return geo_profile
