"""通知模块核心数据模型"""

__all__ = [
    "NotificationContent",
    "NotificationTask",
]

import abc
import typing


class NotificationContent(abc.ABC):
    """通知内容"""

    @abc.abstractmethod
    def to_wxmp_submessage(self) -> "WXMPSubMessageContent":
        """转换为微信小程序订阅消息内容"""
        ...

    @abc.abstractmethod
    def to_wxsa_submessage(self) -> "WXSASubMessageContent":
        """转换为微信服务号订阅消息内容"""
        ...


class NotificationTask(typing.TypedDict):
    to: tuple[str, ...]
    """接收用户"""
    channel: type["NotificationChannelManager"]
    """通知渠道"""
    content: NotificationContent
    """通知内容"""


# TYPE_CHECKING imports
if typing.TYPE_CHECKING:
    from .channel_weixin import WXMPSubMessageContent, WXSASubMessageContent
    from communication.managers.notification.main import NotificationChannelManager
