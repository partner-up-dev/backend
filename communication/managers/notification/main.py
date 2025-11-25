"""通知模块主模块"""

__all__ = [
    "NotificationChannelManager",
    "NotificationManager",
]

import abc
from blue_firmament.manager import BaseManager
from ...schemas.notification import NotificationContent, NotificationTask


class NotificationChannelManager(BaseManager, abc.ABC):
    @abc.abstractmethod
    async def send(self, to_users: tuple[str, ...], content: NotificationContent) -> None: ...


class NotificationManager(BaseManager, manager_name="notification"):
    async def send(self, notification_task: NotificationTask) -> None:
        """发送通知"""
        channel = notification_task["channel"]
        await channel(self).send(notification_task["to"], notification_task["content"])
        return None
