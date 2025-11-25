"""沟通模块的数据模型"""

__all__ = [
    "NotificationContent",
    "NotificationTask",
    "WXMPSubMessageContent",
    "WXSASubMessageContent",
]

from .notification import (
    NotificationContent,
    NotificationTask,
    WXMPSubMessageContent,
    WXSASubMessageContent,
)
