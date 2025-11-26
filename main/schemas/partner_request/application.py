"""搭子申请数据模型"""

__all__ = [
    "PartnerApplicationStatus",
    "SubPartnerApplication",
    "PartnerApplicationRef",
    "PartnerApplication",
]

import datetime
import enum
import typing
import sqlalchemy
import sqlmodel
from typing import Optional as Opt, NewType, List
from pydantic import BaseModel

from account.schemas import AccountRef
from .base import PartnerRequestRef
from .partner import PartnerRoleRef


ChatRef: typing.TypeAlias = int


class PartnerApplicationStatus(enum.Enum):
    """搭子申请状态"""

    PENDING = "pending"
    """待审批"""
    APPROVED = "approved"
    """通过"""
    REJECTED = "rejected"
    """拒绝"""
    WITHDRAWN = "withdrawn"
    """已撤回"""
    EXPIRED = "expired"
    """已过期"""

    def is_open(self) -> bool:
        """是否可以操作（审批、撤回、过期等）"""
        return self in self.open_status()

    def is_closed(self) -> bool:
        """是否已关闭"""
        return self in self.closed_status()

    @classmethod
    def closed_status(cls) -> tuple["PartnerApplicationStatus", ...]:
        """属于已关闭的状态"""
        return (cls.APPROVED, cls.REJECTED, cls.WITHDRAWN, cls.EXPIRED)

    @classmethod
    def open_status(cls) -> tuple["PartnerApplicationStatus", ...]:
        """属于开放的状态"""
        return (cls.PENDING,)


class SubPartnerApplication(BaseModel):
    """搭子申请子申请数据模型"""

    role: PartnerRoleRef
    """搭子角色 ID"""
    rationale: Opt[str] = None
    """申请理由"""


PartnerApplicationRef = NewType("PartnerApplicationRef", int)
"""搭子申请 ID"""


class PartnerApplication(sqlmodel.SQLModel, table=True):
    """搭子申请数据模型"""
    __tablename__ = "application"  # type: ignore
    __table_args__ = {"schema": "partner_request"}

    id: Opt[int] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.Integer, primary_key=True, autoincrement=True),
        default=None,
    )
    created_at: datetime.datetime = sqlmodel.Field(
        default_factory=datetime.datetime.now,
        sa_column=sqlalchemy.Column(
            sqlalchemy.TIMESTAMP(timezone=True),
            server_default=sqlalchemy.text("CURRENT_TIMESTAMP"),
        ),
    )
    status: str = sqlmodel.Field(default=PartnerApplicationStatus.PENDING.value)
    partner_request: PartnerRequestRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    )
    """所属搭子请求"""
    applicant: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.String, nullable=False)
    )
    chat: ChatRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    )
    eclose_reason: Opt[str] = sqlmodel.Field(default=None)
    """撤回或驳回的理由"""
    sub_applications: Opt[str] = sqlmodel.Field(default=None)  # JSON array of SubPartnerApplication
