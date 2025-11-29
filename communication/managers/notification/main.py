"""通知模块主模块

Business logic for notification operations using FastAPI patterns.
"""

__all__ = [
    "NotificationChannelManager",
    "NotificationManager",
]

import abc
import structlog
from ...schemas.notification import NotificationContent, NotificationTask


logger = structlog.get_logger(__name__)


class NotificationChannelManager(abc.ABC):
    """通知渠道管理器基类

    定义了发送通知的抽象接口。子类实现具体的发送逻辑。
    """

    @classmethod
    @abc.abstractmethod
    async def send(cls, to_users: tuple[str, ...], content: NotificationContent) -> None:
        """发送通知到指定用户

        :param to_users: 目标用户 ID 列表
        :param content: 通知内容
        """
        ...


class NotificationManager:
    """Notification business logic manager.

    Provides methods for sending notifications through various channels.
    Uses classmethod pattern without BlueFirmament dependencies.
    """

    @classmethod
    async def send(cls, notification_task: NotificationTask) -> None:
        """发送通知

        :param notification_task: 通知任务配置
        """
        channel = notification_task["channel"]
        await channel.send(notification_task["to"], notification_task["content"])
        return None
