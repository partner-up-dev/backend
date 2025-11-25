"""微信通知渠道模块"""

__all__ = []

import datetime
import ssl
from typing import Optional as Opt
import aiohttp
import certifi
from blue_firmament.exceptions import (
    ExternalError,
    RequestFailed,
)
from blue_firmament.utils.datetime_ import get_datetimez

from account.schemas.wxmp import WXMPAccount
from dal import SupabaseServPostgrest

from .main import NotificationChannelManager
from ...schemas.notification import NotificationContent
from libs.weixin import WXMP_MP_API, WXMP_SA_API
from settings.wxmp import get_setting as get_weixin_setting

AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector(
    ssl=ssl.create_default_context(cafile=certifi.where())
)


class AccessToken:
    """微信开放平台 AccessToken

    在 data.settings.weixin 中配置该结构
    ```json
    credentials = {
      "<your app name>": {
        "appid": "<your appid>",
        "secret": "<your app secret>"
      }
    }
    ```
    """

    URL = "https://api.weixin.qq.com/cgi-bin/token"

    def __init__(self, app_name: str) -> None:
        self.__app_name = app_name
        self.__access_token = None
        self.__expire_at: Opt[datetime.datetime] = None

    async def refresh(self):
        self.__access_token, self.__expire_at = await self.__get_access_token(self.__app_name)

    async def is_expired(self) -> bool:
        if self.__expire_at is None:
            return True
        return get_datetimez() >= self.__expire_at

    @classmethod
    async def __get_access_token(cls, app_name: str) -> tuple[str, datetime.datetime]:
        """获取 AccessToken

        :returns : access_token, expire_at
        """
        app_setting = get_weixin_setting().credentials[app_name]
        params = {
            "grant_type": "client_credential",
            "appid": app_setting["appid"],
            "secret": app_setting["secret"],
        }

        async with aiohttp.ClientSession(connector=AIOHTTP_CONNECTOR_GETTER()) as session:
            async with session.get(url=cls.URL, params=params) as res:
                if res.status == 200:
                    res = await res.json()
                    access_token = res.get("access_token", None)
                    if access_token is None:
                        raise ExternalError(
                            "get_weixin_access_token",
                            errcode=res.get("errcode", None),
                            params=params,
                        )
                    else:
                        return access_token, get_datetimez() + datetime.timedelta(
                            seconds=res.get("expires_in", 7200)
                        )

                raise RequestFailed(res)

    async def get_authenticated_url(self, url: str) -> str:
        """为 URL 添加 AccessToken 参数"""
        if self.__access_token is None or self.is_expired():
            await self.refresh()
        if self.__access_token is None:
            raise ValueError("AccessToken invalid")
        return url + "?access_token=" + self.__access_token


class WXMPSubMessageManager(NotificationChannelManager, manager_name="wxmp_sub_message"):
    """微信小程序订阅消息渠道管理器"""

    def __post_init__(self) -> None:
        self.api = WXMP_MP_API(self, "partner_up_wxmp")

    async def send(self, to_users: tuple[str, ...], content: NotificationContent):
        for to_user in to_users:
            to_openid = await SupabaseServPostgrest().select_one(
                WXMPAccount.weixin_mp_openid, to_user
            )
            if to_openid:
                await self.api.send_sub_message(to_openid, dict(content.to_wxmp_submessage()))
            else:
                self._logger.warning("to_user don't has wxmp_openid", to_user=to_user)


class WXSASubMessageManager(NotificationChannelManager, manager_name="wxsa_sub_message"):
    """微信服务号订阅消息渠道管理器"""

    def __post_init__(self) -> None:
        self.api = WXMP_SA_API(self, "partner_up_wxsa")

    async def send(self, to_users: tuple[str, ...], content: NotificationContent):
        for to_user in to_users:
            to_openid = await SupabaseServPostgrest().select_one(
                WXMPAccount.weixin_sa_openid, to_user
            )
            if to_openid:
                await self.api.send_sub_message(to_openid, dict(content.to_wxsa_submessage()))
            else:
                self._logger.warning("to_user don't has wxsa_openid", to_user=to_user)
