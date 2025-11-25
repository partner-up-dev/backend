"""消息（聊天子模块）的主要管理器"""

__all__ = [
    "BaseMessageManager",
    "PlainMessageManager",
    "PartnerApplicationMessageManager",
    "SplitBillMessageManager",
]

import typing
from typing import Annotated as Anno
from typing import Optional as Opt

from dal import DefaultRedis
from blue_firmament import listen_to
from blue_firmament.dal.query_components.modifiers import RangeModifier
from blue_firmament.log import get_logger
from blue_firmament.manager import CommonManager, PresetHandlerConfig
from blue_firmament.task import TaskStatus
from blue_firmament.transport import Method
from account.schemas import AccountRef
from ...schemas.chat import ChatRef
from ...schemas.message import (
    Message,
    MessageRef,
    MessageTV,
    PartnerApplicationMessage,
    PlainMessage,
    SplitBillMessage,
)
from main.schemas.partner_request import PartnerApplication
from main.schemas.split_bill import SplitBill

from ..chat import ChatManager

LOGGER = get_logger(__name__)
REDIS = DefaultRedis()


class BaseMessageManager(
    CommonManager[MessageTV, MessageRef],
    typing.Generic[MessageTV],
    manager_name="message",
    scheme_cls=Message,
    path_prefix=ChatManager.__path_prefix__ + "/message",
    preset_handler_config=PresetHandlerConfig(get=True),
):
    async def get_chat_messages(
        self, chat_id: ChatRef, start: int = 0, offset: int = 6, desc: bool = True
    ) -> typing.Tuple[Message, ...]:
        """获取聊天的消息

        :param chat_id: 聊天 ID
        :param start: 起始消息 ID

            - 从 0 开始
            - 最新消息即 0
        :param offset: 偏移量

            - 默认 6
            - 最小 1，最大 12
        :param desc: 是否降序排列
        """
        return await self._dao.select(
            Message.chat.equals(chat_id),
            Message._id.order_by(desc=desc),
            RangeModifier(start, start + offset),
        )

    async def send(self, *args, **kwargs) -> MessageTV:
        """发送消息

        这是一个抽象方法，请调用具体消息类型的发送方法
        """
        raise NotImplementedError("pls use sub message manager")

    async def _sent(self, message_id: MessageRef):
        self._task_result.status = TaskStatus.CREATED
        await self._emit(".new", parameters={"message_id": message_id})

    @listen_to(None, "/{type}/new", transporters=("event",))
    async def _new_message_to_user_queue(
        self,
        message_id: Opt[MessageRef] = None,
    ):
        self._scheme = await self._get_scheme(message_id)
        chat_members = await ChatManager(self).get_members(chat_id=self._scheme.chat)
        chat_members.difference_update(self._scheme.created_by)
        for chat_member in chat_members:
            await REDIS.push(str(message_id).encode("utf-8"), f"unread_messages:{chat_member}")

    @listen_to(Method.PUT, "/{message_id}/viewed")
    async def mark_as_viewed(self, message_id: Opt[MessageRef] = None):
        """消息已读"""
        return await self.insert_item(
            field=self._scheme_cls.viewed, values=(self._operator.id,), _id=message_id
        )


class PlainMessageManager(
    BaseMessageManager[PlainMessage],
    scheme_cls=PlainMessage,
    manager_name="plain_message",
    path_prefix=BaseMessageManager.__path_prefix__ + "/plain",
):
    @listen_to(Method.POST, "")
    async def send(
        self,
        to_chat: ChatRef,
        body: Anno[str, PlainMessage.content],
        created_by: AccountRef | None = None,
        **kwargs,
    ) -> PlainMessage:
        await self.insert(
            PlainMessage(
                _task_context=self,
                _id=MessageRef(0),
                chat=to_chat,
                created_by=created_by or AccountRef(self._operator.id),
                content=body,
            )
        )
        await self._sent(message_id=self._scheme._id)
        return self._scheme


class PartnerApplicationMessageManager(
    BaseMessageManager[PartnerApplicationMessage],
    scheme_cls=PartnerApplicationMessage,
    manager_name="partner_application_message",
    path_prefix=BaseMessageManager.__path_prefix__ + "/partner_application",
):
    async def send(
        self,
        application: PartnerApplication,
        application_chat_id: ChatRef,
    ) -> PartnerApplicationMessage:
        """发送搭子请求消息

        :param application: 搭子申请
        :param application_chat_id: 所属的搭子申请群聊 ID
        """
        await self.insert(
            PartnerApplicationMessage(
                _task_context=self,
                _id=MessageRef(0),
                chat=application_chat_id,
                created_by=application.applicant,
                content=application._id,
            )
        )
        await self._sent(message_id=self._scheme._id)
        return self._scheme


class SplitBillMessageManager(
    BaseMessageManager[SplitBillMessage],
    scheme_cls=SplitBillMessage,
    manager_name="split_bill_message",
    path_prefix=BaseMessageManager.__path_prefix__ + "/split_bill",
):
    async def send(self, split_bill: SplitBill, chat_id: ChatRef) -> SplitBillMessage:
        """发送分账账单消息"""
        res = await self.insert(
            SplitBillMessage(
                _task_context=self,
                _id=MessageRef(0),
                chat=chat_id,
                created_by=split_bill.created_by,
                content=split_bill._id,
            )
        )
        await self._sent(message_id=res._id)
        return res
