"""微信通知相关数据模型"""

__all__ = [
    "WXMPSubMessageContent",
    "WXSASubMessageContent",
]

import typing


class WXMPSubMessageContent(typing.TypedDict):
    """微信小程序订阅消息内容"""

    template_id: str
    data: dict
    page: typing.NotRequired[str]


class WXSASubMessageContent(typing.TypedDict):
    """微信服务号订阅消息内容"""

    template_id: str
    data: dict
    page: typing.NotRequired[str]
