"""搭子请求合并请求数据模型"""

__all__ = ["PRMergeRequestStatus", "PRMergeRequestRef", "PRMergeRequest"]

import datetime
import enum
import typing
import sqlalchemy
import sqlmodel
from typing import Optional as Opt, NewType

from account.schemas import AccountRef
from .base import PartnerRequestRef


class PRMergeRequestStatus(enum.Enum):
    """搭子请求合并请求状态"""

    DRAFT = "draft"
    PENDING = "pending"
    """等待审批"""
    APPROVED = "approved"
    """已通过"""
    REJECTED = "rejected"
    """已拒绝"""
    EXPIRED = "expired"
    """已过期"""

    def is_open(self) -> bool:
        """是否可操作"""
        return self in (self.DRAFT, self.PENDING)


PRMergeRequestRef = NewType("PRMergeRequestRef", int)
"""搭子请求合并请求ID"""


class PRMergeRequest(sqlmodel.SQLModel, table=True):
    """搭子请求合并请求"""
    __tablename__ = "merge_request"  # type: ignore
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
    created_by: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.String, nullable=False)
    )
    status: str = sqlmodel.Field(default=PRMergeRequestStatus.DRAFT.value)
    froms: Opt[str] = sqlmodel.Field(default=None)  # JSON array of PartnerRequestRef
    """被合并的搭子请求"""
    to: Opt[PartnerRequestRef] = sqlmodel.Field(default=None)
    """合并后的搭子请求 ID"""
    n_title: Opt[str] = sqlmodel.Field(default=None)
    n_introduction: Opt[str] = sqlmodel.Field(default=None)
    n_created_by: Opt[str] = sqlmodel.Field(default=None)
    n_partners: Opt[str] = sqlmodel.Field(default=None)  # JSON array
    n_typed_content: Opt[str] = sqlmodel.Field(default=None)  # JSON object
