"""聊天模块的核心数据模型"""

__all__ = [
    "MessageType",
    "MessageRef",
    "Message",
]

import datetime
import enum
import sqlalchemy
import sqlmodel
from typing import Optional as Opt, NewType
from pydantic import BaseModel

from account.schemas import AccountRef
from ..chat import ChatRef


class MessageType(enum.Enum):
    """消息内容类型"""

    PLAIN = "plain"
    """纯文本"""
    RICH = "rich"
    """富文本"""
    IMAGE = "image"
    """图片"""
    PARTNER_APPLICATION = "partner_application"
    """搭子申请"""
    SPLIT_BILL = "split_bill"
    """分账账单"""
    THREAD_ENTRY = "thread_entry"
    """聊天邀请"""
    APPROVAL = "approval"
    """审批"""


MessageRef = NewType("MessageRef", int)
"""消息 ID"""


class Message(sqlmodel.SQLModel, table=True):
    """消息数据模型"""
    __tablename__ = "message"  # type: ignore
    __table_args__ = {"schema": "chat"}

    id: Opt[int] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.Integer, primary_key=True, autoincrement=True),
        default=None,
    )
    chat: ChatRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    )
    created_at: datetime.datetime = sqlmodel.Field(
        default_factory=datetime.datetime.now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.TIMESTAMP(timezone=True),
            server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
        ),
    )
    created_by: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.String, nullable=False)
    )
    viewed: Opt[str] = sqlmodel.Field(default=None)  # JSON array of AccountRef
    """已读用户列表"""
    forwarded_from: Opt[int] = sqlmodel.Field(default=None)
    """转发自"""
    replied_to: Opt[int] = sqlmodel.Field(default=None)
    """回复至"""
    type: str = sqlmodel.Field(
        default=MessageType.PLAIN.value,
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    )
    """消息类型"""
    content: str = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    )


class MessageEditable(BaseModel):
    """Editable fields for Message."""
    type: Opt[MessageType] = None
    content: Opt[str] = None
