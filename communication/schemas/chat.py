"""聊天模块核心数据模型"""

import datetime
import enum
import typing
import sqlalchemy
import sqlmodel
from typing import Optional as Opt

from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    pass


class ChatStatus(enum.Enum):
    """聊天状态"""

    OPEN = "open"
    BLOCKED = "blocked"
    CLOSED = "closed"


class ChatType(enum.Enum):
    """聊天类型"""

    DIRECT_MESSAGE = "direct_message"
    """私信"""
    PARTNER_REQUEST = "partner_request"
    """搭子请求群聊"""
    PARTNER_APPLICATION = "partner_application"
    """搭子申请群聊"""


ChatRef: typing.TypeAlias = int
"""聊天 ID"""


class Chat(sqlmodel.SQLModel, table=True):
    """聊天数据模型"""

    __tablename__ = "chat"  # type: ignore
    __table_args__ = {"schema": "communication"}

    id: Opt[ChatRef] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.Integer, primary_key=True, autoincrement=True),
        default=None,
    )
    type: str = sqlmodel.Field(sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False))
    status: str = sqlmodel.Field(default=ChatStatus.OPEN.value)
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
    """创建者，即管理员"""
    title: Opt[str] = sqlmodel.Field(default=None)
    avatar: Opt[str] = sqlmodel.Field(default=None)
    parent: Opt[ChatRef] = sqlmodel.Field(default=None)
    """父聊天"""
    members: Opt[str] = sqlmodel.Field(default=None)  # JSON array of AccountRef
    """成员列表

    类型为搭子请求、搭子申请群聊时为 None
    """
