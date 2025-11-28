# author: Lan_zhijiang
# date: 2024/06/03
# desc: Weixin Platform Related API

import datetime
import aiohttp
import platform
import structlog
from typing import Optional as Opt
from fastapi import HTTPException

from core.settings import get_settings

if platform.system() == "Darwin":
    import ssl, certifi

    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector(
        ssl=ssl.create_default_context(cafile=certifi.where())
    )
else:
    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector()


logger = structlog.get_logger("WXMP_LIB")


class MPWX_APIError(Exception):
    """微信小程序 API 错误"""

    def __init__(self, service_name: str, errcode: int, message: Opt[str] = None, **kwargs):
        self.service_name = service_name
        self.errcode = errcode
        self.message = message
        super().__init__(f"{service_name}: errcode={errcode}, message={message}")


class NotSubscribed(Exception):
    """用户未订阅该消息"""

    def __init__(self, to: str, template_id: str):
        msg = f"user {to} not subscribed this template, {template_id}"
        super().__init__(msg)


class WXMP_APP:
    """微信开放平台应用基类"""

    def __init__(self, app_name: str) -> None:
        self.__app_name = app_name
        self.__access_token = None
        self.__expire_at: Opt[datetime.datetime] = None
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Load credentials from settings."""
        settings = get_settings()
        if self.__app_name == "partner_up_wxmp":
            self.__appid = settings.weixin_partner_up_wxmp_appid
            self.__secret = settings.weixin_partner_up_wxmp_secret
        elif self.__app_name == "partner_up_wxsa":
            self.__appid = settings.weixin_partner_up_wxsa_appid
            self.__secret = settings.weixin_partner_up_wxsa_secret
        else:
            raise ValueError(f"Unknown app name: {self.__app_name}")

    @property
    def _id(self) -> str:
        """应用ID (AppID)"""
        return self.__appid

    @property
    def _secret(self) -> str:
        """应用密钥 (App Secret)"""
        return self.__secret

    async def _refresh(self):
        """刷新AccessToken"""
        self.__access_token, self.__expire_at = await self.__get_access_token()

    async def _is_token_expired(self) -> bool:
        """检查AccessToken是否过期"""
        if self.__expire_at is None:
            return True
        return datetime.datetime.now(datetime.timezone.utc) >= self.__expire_at

    async def __get_access_token(self) -> tuple[str, datetime.datetime]:
        """获取 AccessToken

        :returns : access_token, expire_at
        """
        params = {
            "grant_type": "client_credential",
            "appid": self._id,
            "secret": self._secret,
        }

        async with aiohttp.ClientSession(connector=AIOHTTP_CONNECTOR_GETTER()) as session:
            async with session.get(
                url="https://api.weixin.qq.com/cgi-bin/token", params=params
            ) as res:
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
                        ) + datetime.timedelta(
                            seconds=res_data.get("expires_in", 7200)
                        )

                raise HTTPException(status_code=502, detail="Failed to get access token")

    async def _get_access_token(self) -> str:
        """获取访问令牌字符串"""
        if self.__access_token is None or await self._is_token_expired():
            await self._refresh()
        if self.__access_token is None:
            raise ValueError("AccessToken invalid")
        return self.__access_token

    async def request(
        self, method: str, url: str, service_name: str = "weixin_api", **kwargs
    ) -> dict:
        """请求WXMP_API"""
        retry_count = kwargs.pop("retry_count", 2)

        for attempt in range(retry_count + 1):
            try:
                # 获取 access_token 并添加到 URL
                token = await self._get_access_token()
                full_url = url + "?access_token=" + token

                async with aiohttp.ClientSession(
                    connector=AIOHTTP_CONNECTOR_GETTER()
                ) as session:
                    async with session.request(method.upper(), full_url, **kwargs) as response:
                        response_data = await response.json()

                        # 检查 Weixin API 错误码
                        errcode = response_data.get("errcode")
                        if errcode is not None and errcode != 0:
                            if errcode in (40001, 42001):  # access_token 无效
                                if attempt < retry_count:
                                    logger.warning(
                                        f"Access token invalid (errcode: {errcode}), refreshing"
                                    )
                                    await self._refresh()
                                    continue
                                else:
                                    raise HTTPException(
                                        status_code=401,
                                        detail=f"Weixin access token invalid (errcode: {errcode})"
                                    )
                            elif errcode == 45011:  # 请求频率限制
                                raise HTTPException(status_code=429, detail="Too many requests")
                            elif errcode in (40029, 40163):  # invalid code (or used)
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Invalid or used code (errcode: {errcode})"
                                )
                            else:
                                raise MPWX_APIError(
                                    service_name,
                                    errcode,
                                    message=response_data.get("errmsg", "Unknown error"),
                                )

                        return response_data

            except aiohttp.ClientError as e:
                if attempt < retry_count:
                    logger.warning(f"Request failed, retrying ({attempt + 1}/{retry_count}): {e}")
                    continue
                raise HTTPException(status_code=502, detail=f"Request failed: {e}")

        raise HTTPException(status_code=502, detail="Request failed after all retries")


class WXMP_MP_API(WXMP_APP):
    """微信公众号平台小程序API客户端"""

    def __init__(self, app_name: str = "partner_up_wxmp") -> None:
        super().__init__(app_name)

    @classmethod
    async def get_openid(cls, code: str) -> tuple[str, str]:
        """使用 jscode 获取 OpenID, UnionID

        :param code: 小程序在 wx.login 响应中拿到的 code
        :return: openid, unionid
        """
        instance = cls()
        params = {
            "appid": instance._id,
            "secret": instance._secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }

        url = "https://api.weixin.qq.com/sns/jscode2session"
        response_data = await instance.request(
            "GET", url, params=params, service_name="wxmp_mp_jscode2session"
        )

        return response_data["openid"], response_data.get("unionid", "")


class WXMP_SA_API(WXMP_APP):
    """微信公众号平台服务号API客户端"""

    def __init__(self, app_name: str = "partner_up_wxsa") -> None:
        super().__init__(app_name)

    @classmethod
    async def get_openid(cls, code: str) -> tuple[str, str]:
        """使用 OAuth2 code 获取 OpenID, UnionID

        :param code: 在 Redirect URL 中提供的 code 查询参数
        :return: openid, unionid
        """
        instance = cls()
        params = {
            "appid": instance._id,
            "secret": instance._secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        response_data = await instance.request(
            "GET", url, params=params, service_name="wxmp_sa_oauth2_access_token"
        )

        return response_data["openid"], response_data.get("unionid", "")
