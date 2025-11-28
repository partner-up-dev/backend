"""WXMP Account Manager."""

import jwt
import time
import uuid
import structlog
from typing import Optional as Opt
from fastapi import HTTPException
import sqlmodel

from core.settings import get_settings
from libs.weixin import WXMP_MP_API, WXMP_SA_API
from .account import SupabaseAuth
from ..schemas import BaseProfile
from ..schemas.manager import V2WXMPLoginBody
from ..schemas.wxmp import WXMPAccount, WXMPClientType


logger = structlog.get_logger(__name__)


async def wxmp_login(
    db: sqlmodel.Session,
    client_type: WXMPClientType,
    body: V2WXMPLoginBody,
) -> tuple[BaseProfile, str, Opt[str]]:
    """微信公众平台登录

    :param db: Database session
    :param client_type: 客户端类型
    :param body: 登录请求体
    :returns: (profile, access_token, refresh_token)
    """
    settings = get_settings()

    # get openid
    unionid = None
    if client_type == WXMPClientType.MINIPROGRAM:
        openid, unionid = await WXMP_MP_API.get_openid(body.code)
    elif client_type == WXMPClientType.SERVICE_ACCOUNT:
        openid, unionid = await WXMP_SA_API.get_openid(body.code)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported WXMP Client Type {client_type}")

    openid_field = WXMPAccount.get_openid_field_name(client_type)

    # Try to find by openid
    statement = sqlmodel.select(WXMPAccount).where(
        getattr(WXMPAccount, openid_field) == openid
    )
    wxmp_account = db.exec(statement).first()

    if not wxmp_account and unionid:
        # Try to find by unionid
        statement = sqlmodel.select(WXMPAccount).where(
            WXMPAccount.weixin_unionid == unionid
        )
        wxmp_account = db.exec(statement).first()

        if wxmp_account:
            # Link openid
            setattr(wxmp_account, openid_field, openid)
            db.add(wxmp_account)
            db.commit()

    if not wxmp_account:
        # Create new account
        supa_auth_client = SupabaseAuth.get_anon_client()
        signin_res = await supa_auth_client.sign_in_anonymously()
        if signin_res.user is None or signin_res.session is None:
            raise HTTPException(status_code=503, detail="Auth service unavailable")

        account = signin_res.user
        session = signin_res.session

        wxmp_account = WXMPAccount(id=account.id, weixin_unionid=unionid)
        wxmp_account.set_openid(client_type, openid)
        db.add(wxmp_account)

        profile = BaseProfile(id=account.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

        return profile, session.access_token, session.refresh_token

    # Generate JWT for existing account
    payload = {
        "sub": wxmp_account.id,
        "iss": "partnerup-backend/account",
        "session_id": uuid.uuid4().hex,
        "iat": int(time.time()),
        "exp": int(time.time()) + 60 * 60,
        "aud": "authenticated",
        "role": "authenticated",
        "is_anonymous": True,
    }
    access_token = jwt.encode(
        payload,
        key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithms[0],
    )

    profile = db.get(BaseProfile, wxmp_account.id)
    if not profile:
        profile = BaseProfile(id=wxmp_account.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile, access_token, None
