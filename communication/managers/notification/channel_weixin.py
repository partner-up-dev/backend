"""微信通知渠道模块

Business logic for WeChat notification channels using FastAPI patterns.
"""

__all__ = [
    "WXMPSubMessageManager",
    "WXSASubMessageManager",
]

import datetime
import ssl
import platform
from typing import Optional as Opt
import aiohttp
import structlog

from fastapi import HTTPException

from core.engine import SessionLocal
from account.schemas.wxmp import WXMPAccount

from .main import NotificationChannelManager
from ...schemas.notification import NotificationContent
from core.settings import get_settings


# Platform-specific SSL configuration
if platform.system() == "Darwin":
    import certifi

    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector(
        ssl=ssl.create_default_context(cafile=certifi.where())
    )
else:
    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector()


logger = structlog.get_logger(__name__)


class AccessToken:
    """微信开放平台 AccessToken

    用于管理微信 API 访问令牌。
    """

    URL = "https://api.weixin.qq.com/cgi-bin/token"

    def __init__(self, app_name: str) -> None:
        self.__app_name = app_name
        self.__access_token: Opt[str] = None
        self.__expire_at: Opt[datetime.datetime] = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from settings."""
        settings = get_settings()
        if self.__app_name == "partner_up_wxmp":
            self.__appid = settings.weixin.partner_up_wxmp_appid
            self.__secret = settings.weixin.partner_up_wxmp_secret
        elif self.__app_name == "partner_up_wxsa":
            self.__appid = settings.weixin.partner_up_wxsa_appid
            self.__secret = settings.weixin.partner_up_wxsa_secret
        else:
            raise ValueError(f"Unknown app name: {self.__app_name}")

    async def refresh(self):
        self.__access_token, self.__expire_at = await self.__get_access_token()

    def is_expired(self) -> bool:
        if self.__expire_at is None:
            return True
        return datetime.datetime.now(datetime.timezone.utc) >= self.__expire_at

    async def __get_access_token(self) -> tuple[str, datetime.datetime]:
        """获取 AccessToken

        :returns : access_token, expire_at
        """
        params = {
            "grant_type": "client_credential",
            "appid": self.__appid,
            "secret": self.__secret,
        }

        async with aiohttp.ClientSession(connector=AIOHTTP_CONNECTOR_GETTER()) as session:
            async with session.get(url=self.URL, params=params) as res:
                if res.status == 200:
                    res_data = await res.json()
                    access_token = res_data.get("access_token", None)
                    if access_token is None:
                        raise HTTPException(
                            status_code=502,
                            detail=f"Failed to get access token: {res_data.get('errcode')}"
                        )
                    else:
                        return access_token, datetime.datetime.now(
                            datetime.timezone.utc
                        ) + datetime.timedelta(seconds=res_data.get("expires_in", 7200))

                raise HTTPException(status_code=502, detail="Failed to get access token")

    async def get_access_token(self) -> str:
        """获取访问令牌字符串"""
        if self.__access_token is None or self.is_expired():
            await self.refresh()
        if self.__access_token is None:
            raise ValueError("AccessToken invalid")
        return self.__access_token


class WXMPSubMessageManager(NotificationChannelManager):
    """微信小程序订阅消息渠道管理器

    Provides methods for sending subscription messages via WeChat Mini Program.
    """

    SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"
    _access_token: Opt[AccessToken] = None

    @classmethod
    def _get_access_token(cls) -> AccessToken:
        """Get or create AccessToken instance."""
        if cls._access_token is None:
            cls._access_token = AccessToken("partner_up_wxmp")
        return cls._access_token

    @classmethod
    def _get_openid(cls, user_id: str) -> Opt[str]:
        """Get WeChat OpenID for a user."""
        with SessionLocal() as db:
            wxmp_account = db.get(WXMPAccount, user_id)
            if wxmp_account:
                return wxmp_account.weixin_mp_openid
            return None

    @classmethod
    async def send(cls, to_users: tuple[str, ...], content: NotificationContent) -> None:
        """发送微信小程序订阅消息

        :param to_users: 目标用户 ID 列表
        :param content: 通知内容
        """
        token_manager = cls._get_access_token()
        access_token = await token_manager.get_access_token()

        for to_user in to_users:
            to_openid = cls._get_openid(to_user)
            if to_openid:
                msg_content = content.to_wxmp_submessage()
                await cls._send_message(access_token, to_openid, msg_content)
            else:
                logger.warning("to_user doesn't have wxmp_openid", to_user=to_user)

    @classmethod
    async def _send_message(cls, access_token: str, to_openid: str, content: dict) -> None:
        """Send subscription message to a specific user."""
        url = f"{cls.SEND_URL}?access_token={access_token}"
        payload = {
            "touser": to_openid,
            "template_id": content["template_id"],
            "data": content["data"],
        }
        if "page" in content:
            payload["page"] = content["page"]

        async with aiohttp.ClientSession(connector=AIOHTTP_CONNECTOR_GETTER()) as session:
            async with session.post(url, json=payload) as res:
                res_data = await res.json()
                errcode = res_data.get("errcode", 0)
                if errcode != 0:
                    logger.error(
                        "Failed to send subscription message",
                        errcode=errcode,
                        errmsg=res_data.get("errmsg"),
                        to_openid=to_openid,
                    )


class WXSASubMessageManager(NotificationChannelManager):
    """微信服务号订阅消息渠道管理器

    Provides methods for sending subscription messages via WeChat Service Account.
    """

    SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/template/subscribe"
    _access_token: Opt[AccessToken] = None

    @classmethod
    def _get_access_token(cls) -> AccessToken:
        """Get or create AccessToken instance."""
        if cls._access_token is None:
            cls._access_token = AccessToken("partner_up_wxsa")
        return cls._access_token

    @classmethod
    def _get_openid(cls, user_id: str) -> Opt[str]:
        """Get WeChat Service Account OpenID for a user."""
        with SessionLocal() as db:
            wxmp_account = db.get(WXMPAccount, user_id)
            if wxmp_account:
                return wxmp_account.weixin_sa_openid
            return None

    @classmethod
    async def send(cls, to_users: tuple[str, ...], content: NotificationContent) -> None:
        """发送微信服务号订阅消息

        :param to_users: 目标用户 ID 列表
        :param content: 通知内容
        """
        token_manager = cls._get_access_token()
        access_token = await token_manager.get_access_token()

        for to_user in to_users:
            to_openid = cls._get_openid(to_user)
            if to_openid:
                msg_content = content.to_wxsa_submessage()
                await cls._send_message(access_token, to_openid, msg_content)
            else:
                logger.warning("to_user doesn't have wxsa_openid", to_user=to_user)

    @classmethod
    async def _send_message(cls, access_token: str, to_openid: str, content: dict) -> None:
        """Send subscription message to a specific user."""
        url = f"{cls.SEND_URL}?access_token={access_token}"
        payload = {
            "touser": to_openid,
            "template_id": content["template_id"],
            "data": content["data"],
        }
        if "page" in content:
            payload["page"] = content["page"]

        async with aiohttp.ClientSession(connector=AIOHTTP_CONNECTOR_GETTER()) as session:
            async with session.post(url, json=payload) as res:
                res_data = await res.json()
                errcode = res_data.get("errcode", 0)
                if errcode != 0:
                    logger.error(
                        "Failed to send subscription message",
                        errcode=errcode,
                        errmsg=res_data.get("errmsg"),
                        to_openid=to_openid,
                    )
