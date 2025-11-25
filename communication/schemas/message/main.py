"""聊天模块的核心数据模型"""

__all__ = [
    "MessageType",
    "MessageTV",
    "MessageRef",
    "Message",
    "MessageEditable",
    "PlainMessage",
    "PartnerApplicationMessage",
    "SplitBillMessage",
    "ThreadEntryMessage",
    "ApprovalMessage",
]

import datetime
import typing
import enum
from typing import Optional as Opt
import typing_extensions
from blue_firmament.scheme import (
    BaseScheme,
    BusinessScheme,
    FieldT,
    field,
    field_validator,
    StrConverter,
)
from .thread_entry import ThreadEntry
from dal import SupabaseAnonPostgrest
from blue_firmament.scheme.field import Field
from blue_firmament.utils.datetime_ import get_datetimez
from blue_firmament.task.context import SoCommonTC
from blue_firmament.exceptions import Forbidden
from .approval import Approval
from account.schemas import AccountRef
from ..chat import Chat, ChatRef
from main.schemas.split_bill import SplitBillRef
from main.schemas.partner_request.application import PartnerApplicationRef


class MessageType(enum.Enum):
    """消息内容类型"""

    PLAIN = "plain"
    """纯文本
    """
    RICH = "rich"
    """富文本
    """
    IMAGE = "image"
    """图片
    """
    PARTNER_APPLICATION = "partner_application"
    """搭子申请"""
    SPLIT_BILL = "split_bill"
    """分账账单"""
    THREAD_ENTRY = "thread_entry"
    """聊天邀请"""
    APPROVAL = "approval"
    """审批"""


MessageRef = typing.NewType("MessageRef", int)
"""消息 ID"""


class Message(
    BusinessScheme[MessageRef],
    SoCommonTC,
    key_type=MessageRef,
    dal=SupabaseAnonPostgrest,
    dal_path=("message", "chat"),
):
    """消息数据模型"""

    chat: FieldT[ChatRef]
    created_at: FieldT[datetime.datetime] = field(default_factory=get_datetimez)
    created_by: FieldT[AccountRef] = field()
    viewed: FieldT[typing.Set[AccountRef]] = field(default_factory=set)
    """已读用户列表

    不包括创建者（非强约束）
    """
    forwarded_from: Opt[MessageRef] = None
    """转发自
    """
    replied_to: Opt[MessageRef] = None
    """回复至
    """
    type: FieldT[MessageType]
    """消息类型
    """
    content: FieldT[typing.Any]

    @field_validator(created_by)
    async def must_be_member(self, value: AccountRef):
        """创建者必须是聊天成员

        - 仅在创建前校验
        - TODO 排除全局账号
        """
        if not self._inserted:
            chat_members = await (await self._daos(Chat).select_one(self.chat)).get_members()
            if value not in chat_members:
                raise Forbidden("created_by is not a member of chat")


MessageTV = typing_extensions.TypeVar("MessageTV", bound=Message, default=Message)


class MessageEditable(BaseScheme, proxy=False, partial=True):
    type: MessageType
    content: typing.Any


class PlainMessage(Message, inherit_validators=True):
    """纯文本消息"""

    type: FieldT[MessageType] = field(default=MessageType.PLAIN)
    content: FieldT[str] = field(converter=StrConverter(min=1, max=120))


class PartnerApplicationMessage(Message, inherit_validators=True):
    """搭子申请消息"""

    type: FieldT[MessageType] = field(default=MessageType.PARTNER_APPLICATION)
    content: FieldT[PartnerApplicationRef]


class SplitBillMessage(Message, inherit_validators=True):
    """分账账单消息"""

    type: FieldT[MessageType] = field(default=MessageType.SPLIT_BILL)
    content: FieldT[SplitBillRef]


class ThreadEntryMessage(Message, inherit_validators=True):
    """聊天邀请消息"""

    type: FieldT[MessageType] = field(default=MessageType.THREAD_ENTRY)
    content: FieldT[ThreadEntry]


class ApprovalMessage(Message, inherit_validators=True):
    """审批消息"""

    type: FieldT[MessageType] = field(default=MessageType.APPROVAL)
    content: Field[Approval]
