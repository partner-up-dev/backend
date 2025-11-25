# author: Lan_zhijiang
# date: 2024/06/03
# desc: Weixin Platform Related API

import datetime
import typing
import aiohttp
import platform
from typing import Optional as Opt
from blue_firmament.manager import BaseManager
from blue_firmament.exceptions import (
    ParamsInvalid,
    ExternalError,
    Unauthorized,
    RequestFailed,
    TooManyRequests,
)
from blue_firmament.log import get_logger
from blue_firmament.utils.datetime_ import get_datetimez
from settings.wxmp import get_setting as get_wxmp_setting

if typing.TYPE_CHECKING:
    from blue_firmament.task.context import BaseTaskContext

if platform.system() == "Darwin":
    import ssl, certifi

    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector(
        ssl=ssl.create_default_context(cafile=certifi.where())
    )
else:
    AIOHTTP_CONNECTOR_GETTER = lambda: aiohttp.TCPConnector()


LOGGER = get_logger("WXMP_LIB")


class MPWX_APIError(ExternalError):
    """微信小程序 API 错误"""

    def __init__(self, service_name: str, errcode: int, message: Opt[str] = None, **kwargs):
        super().__init__(service_name, message=message, **kwargs)
        self.errcode = errcode


class NotSubscribed(Unauthorized):
    """用户未订阅该消息"""

    def __init__(self, to: str, template_id: str):
        msg = f"user {to} not subscribed this template, {template_id}"
        super().__init__(msg)


class WXMP_APP(BaseManager):
    """微信开放平台应用基类

    在 settings.wxmp 中配置该结构
    ```json
    credentials = {
      "<your app name>": {
        "appid": "<your appid>",
        "secret": "<your app secret>"
      }
    }
    ```
    """

    def __init__(self, task_context: "BaseTaskContext", app_name: str) -> None:
        super().__init__(task_context)
        self.__app_name = app_name

    def __post_init__(self) -> None:
        """自定义初始化行为"""
        # 加载 credentials
        self.__credentials = get_wxmp_setting().credentials[self.__app_name]
        self.__access_token = None
        self.__expire_at: Opt[datetime.datetime] = None

    @property
    def _id(self) -> str:
        """应用ID (AppID)"""
        return self.__credentials["appid"]

    @property
    def _secret(self) -> str:
        """应用密钥 (App Secret)"""
        return self.__credentials["secret"]

    async def _refresh(self):
        """刷新AccessToken"""
        self.__access_token, self.__expire_at = await self.__get_access_token()

    async def _is_token_expired(self) -> bool:
        """检查AccessToken是否过期"""
        if self.__expire_at is None:
            return True
        return get_datetimez() >= self.__expire_at

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
        """请求WXMP_API

        处理 access_token 和 Weixin API 错误

        :param method: HTTP 方法 ('GET', 'POST', etc.)
        :param url: 请求 URL
        :param kwargs: 可选参数，包括：
            - params: URL 参数
            - data: 表单数据
            - json: JSON 数据
            - headers: 请求头
            - retry_count: 重试次数 (默认 2)
        :return: 解析后的 JSON 响应
        """
        retry_count = kwargs.pop("retry_count", 2)

        for attempt in range(retry_count + 1):
            try:
                # 获取 access_token 并添加到 URL
                token = await self._get_access_token()
                url = url + "?access_token=" + token

                # 准备请求参数
                request_kwargs = {
                    "method": method.upper(),
                    "url": url,
                    "connector": AIOHTTP_CONNECTOR_GETTER(),
                    **kwargs,
                }

                async with aiohttp.ClientSession() as session:
                    async with session.request(**request_kwargs) as response:
                        response_data = await response.json()

                        # 检查 Weixin API 错误码
                        errcode = response_data.get("errcode")
                        if errcode is not None and errcode != 0:
                            if errcode in (40001, 42001):  # access_token 无效
                                if attempt < retry_count:
                                    msg = f"Access token invalid (errcode: {errcode})"
                                    LOGGER.warning(f"{msg}, refreshing and retrying")
                                    await self._refresh()
                                    continue
                                else:
                                    raise Unauthorized(
                                        f"Weixin access token invalid (errcode: {errcode})",
                                        identity=token,
                                    )
                            elif errcode == 45011:  # 请求频率限制
                                raise TooManyRequests(url=url)
                            elif errcode in (40029, 40163):  # invalid code (or used)
                                raise ParamsInvalid(
                                    f"Invalid or used code (errcode: {errcode})",
                                    code=kwargs.get("params", {}).get("code"),
                                    js_code=kwargs.get("params", {}).get("js_code"),
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
                    LOGGER.warning(f"Request failed, retrying ({attempt + 1}/{retry_count}): {e}")
                    continue
                raise RequestFailed(e)

        raise RequestFailed("Request failed after all retries")


class WXMP_MP_API(WXMP_APP):
    """微信公众号平台小程序API客户端"""

    def __init__(
        self, task_context: "BaseTaskContext", app_name: str = "partner_up_wxmp"
    ) -> None:
        super().__init__(task_context, app_name)

    async def get_openid(self, code: str) -> tuple[str, str]:
        """使用 jscode 获取 OpenID, UnionID

        :param code: 小程序在 wx.login 响应中拿到的 code
        :return: openid, unionid

        :docs: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
        """
        params = {
            "appid": self._id,
            "secret": self._secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }

        url = "https://api.weixin.qq.com/sns/jscode2session"
        response_data = await self.request(
            "GET", url, params=params, service_name="wxmp_mp_jscode2session"
        )

        return response_data["openid"], response_data["unionid"]

    async def msg_sec_check(self, content: str, openid: str) -> bool:
        """文本类型内容安全检测

        :param content: 要检测的内容
        :param openid: 用户OpenID
        :return: bool 是否通过

        :docs: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/sec-center/sec-check/msgSecCheck.html
        """
        url = "https://api.weixin.qq.com/wxa/msg_sec_check"
        params = {"content": content, "version": 2, "scene": 2, "openid": openid}

        response_data = await self.request("POST", url, json=params)

        # validate if pass
        suggest = response_data["result"]["suggest"]
        if suggest == "pass":
            return True
        else:
            LOGGER.warning("%s for content %s", suggest, content)
            return False

    async def get_phone_number(self, code: str) -> str:
        """获取用户手机号

        :param code: 小程序端获取的手机号获取凭证
        :return: 用户手机号

        :docs: https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-info/phone-number/getPhoneNumber.html#%E4%BA%91%E8%B0%83%E7%94%A8
        """
        url = "https://api.weixin.qq.com/wxa/business/getuserphonenumber"
        params = {"code": code}
        response_data = await self.request(
            "POST", url, json=params, service_name="wxmp_mp_getphonenumber"
        )

        return response_data["phone_info"]["phoneNumber"]

    async def send_sub_message(self, to_openid: str, content: dict) -> None:
        """发送订阅消息

        :param to_openid: 接收用户的 OpenID
        :param content: 消息内容，包含 template_id, data 等
        """
        url = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"
        req_body = {
            "touser": to_openid,
            "miniprogram_state": "formal",
            "lang": "zh_CN",
            **content,
        }

        try:
            response_data = await self.request(
                "POST", url, json=req_body, service_name="wxmp_send_sub_message"
            )
        except MPWX_APIError as e:
            if e.errcode == 43101:
                raise NotSubscribed(to=to_openid, template_id=content.get("template_id") or "")


class WXMP_SA_API(WXMP_APP):
    """微信公众号平台服务号API客户端"""

    def __init__(
        self, task_context: "BaseTaskContext", app_name: str = "partner_up_wxsa"
    ) -> None:
        super().__init__(task_context, app_name)

    async def get_openid(self, code: str) -> tuple[str, str]:
        """使用 OAuth2 code 获取 OpenID, UnionID

        :param code: 在 Redirect URL 中提供的 code 查询参数
        :return: openid, unionid

        :docs: https://developers.weixin.qq.com/doc/offiaccount/OA_Web_Apps/Wechat_webpage_authorization.html
        """
        params = {
            "appid": self._id,
            "secret": self._secret,
            "code": code,
            "grant_type": "authorization_code",
        }

        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        response_data = await self.request(
            "GET", url, params=params, service_name="wxmp_sa_oauth2_access_token"
        )

        return response_data["openid"], response_data["unionid"]

    async def send_sub_message(self, to_openid: str, content: dict) -> None:
        """发送订阅消息

        :param to_openid: 接收用户的 OpenID
        :param content: 消息内容，包含 template_id, data 等
        """
        url = "https://api.weixin.qq.com/cgi-bin/message/subscribe/bizsend"
        req_body = {"touser": to_openid, **content}
        await self.request("POST", url, json=req_body, service_name="wxsa_send_sub_message")


# TODO: 需要重构以下函数以适配新的架构
# 这些函数依赖于全局变量 access_token 和 weixin_api_setting，需要重新设计

# @retry_wrapper
# def send_message(template_id: str, page: str, to_user: str, data: dict) -> bool:
#     """
#     发送订阅消息
#     """
#     pass

# def construct_message_data(name: str, data: dict) -> dict:
#     """
#     构建订阅消息内容
#     """
#     pass

# def get_message_template_id(name: str) -> str:
#     """
#     获取订阅消息模板id
#     """
#     pass

# @retry_wrapper
# def verify_soter_result(openid: str, result_json: str, result_json_signature: str) -> bool:
#     """
#     校验微信生物认证结果是否可靠谱
#     """
#     pass

# def get_phone_number(code: str) -> str:
#     """
#     获取手机号
#     """
#     pass
