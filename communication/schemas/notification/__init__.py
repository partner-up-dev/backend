"""通知模块数据模型"""

__all__ = [
    "NotificationContent",
    "NotificationTask",
    "WXMPSubMessageContent",
    "WXSASubMessageContent",
]

from .main import NotificationContent, NotificationTask
from .channel_weixin import WXMPSubMessageContent, WXSASubMessageContent
