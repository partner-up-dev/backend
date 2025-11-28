"""搭子请求基础数据模型"""

import datetime
import enum
import typing
import sqlalchemy
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    pass


PartnerRequestRef: typing.TypeAlias = int
ContractRef: typing.TypeAlias = int


class PartnerRequestType(enum.Enum):
    TRIP = "trip"
    """出行搭子"""
    RIDE_HAILING = "ride_hailing"
    """网约车搭子"""
    COMMUTE = "commute"
    """通勤搭子"""
    HITCHHIKING = "hitchhiking"
    """便车搭子"""
    MOPED = "moped"
    """电瓶搭子"""
    TRAVEL = "travel"
    """旅游搭子"""


class PartnerRequestL2Type(enum.Enum):
    """搭子请求二级类型"""

    # 出行搭子
    RIDE_HAILING = "ride_hailing"
    """网约车搭子"""
    COMMUTE = "commute"
    """通勤搭子"""
    HITCHHIKING = "hitchhiking"
    """便车搭子"""
    MOPED = "moped"
    """电瓶搭子"""

    # 旅游搭子
    TRAVEL = "travel"
    """旅游搭子"""


class PartnerRequestStatus(enum.Enum):
    """搭子请求状态"""

    DRAFT = "draft"
    JOINABLE = "joinable"
    """可加入"""
    READY = "ready"
    """可执行"""
    PERFORMING = "performing"
    """执行中"""
    SETTLING = "settling"
    """结算中"""
    CLOSED = "closed"
    """正常关闭"""
    CANCELLED = "cancelled"
    """取消"""
    MERGED = "merged"
    """已合并"""

    def next(self) -> "PartnerRequestStatus":
        """下一个状态"""
        if self == PartnerRequestStatus.DRAFT:
            return PartnerRequestStatus.JOINABLE
        elif self == PartnerRequestStatus.JOINABLE:
            return PartnerRequestStatus.READY
        elif self == PartnerRequestStatus.READY:
            return PartnerRequestStatus.PERFORMING
        elif self == PartnerRequestStatus.PERFORMING:
            return PartnerRequestStatus.SETTLING
        elif self == PartnerRequestStatus.SETTLING:
            return PartnerRequestStatus.CLOSED

        raise ValueError("No next status for %s" % self)

    def is_draft(self) -> bool:
        return self == PartnerRequestStatus.DRAFT

    def is_joinable(self) -> bool:
        """是否可以加入"""
        return self in (PartnerRequestStatus.JOINABLE,)

    @classmethod
    def ongoing_status(cls) -> tuple["PartnerRequestStatus", ...]:
        """进行中的状态"""
        return (
            cls.JOINABLE,
            cls.READY,
            cls.PERFORMING,
            cls.SETTLING,
        )

    @classmethod
    def closed_status(cls) -> tuple["PartnerRequestStatus", ...]:
        """已关闭的状态"""
        return (
            cls.CLOSED,
            cls.CANCELLED,
        )


class PartnerRequestListType(enum.Enum):
    """搭子请求列表类型"""

    FAVORITE = "favorite"
    """收藏的搭子请求"""
    ONGOING = "ongoing"
    """进行中的搭子请求"""
    HISTORY = "history"
    """历史搭子请求"""
    DRAFT = "draft"
    """草稿搭子请求"""


class PartnerRequest(sqlmodel.SQLModel, table=True):
    """Partner request database model."""
    __tablename__ = "partner_request"  # type: ignore
    __table_args__ = {"schema": "base"}

    id: Opt[PartnerRequestRef] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.Integer, primary_key=True, autoincrement=True),
        default=None,
    )
    type: str = sqlmodel.Field(sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False))
    """搭子请求类型"""
    status: str = sqlmodel.Field(default=PartnerRequestStatus.DRAFT.value)
    """搭子请求状态"""
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
    chat: Opt[int] = sqlmodel.Field(default=None)
    contract: Opt[ContractRef] = sqlmodel.Field(default=None)
    title: Opt[str] = sqlmodel.Field(default=None)
    introduction: Opt[str] = sqlmodel.Field(default=None)

    def is_admin(self, account_id: AccountRef) -> bool:
        """是否为管理员"""
        return self.created_by == account_id

    def is_bill_submittable(self) -> bool:
        """是否可以提交账单"""
        return PartnerRequestStatus(self.status) in (
            PartnerRequestStatus.READY,
            PartnerRequestStatus.PERFORMING,
            PartnerRequestStatus.SETTLING,
        )

    def is_deletable(self) -> bool:
        """是否可以删除"""
        return PartnerRequestStatus(self.status) == PartnerRequestStatus.DRAFT

    def is_mergeable(self) -> bool:
        """是否可以被合并"""
        return PartnerRequestStatus(self.status) == PartnerRequestStatus.JOINABLE


class PRTypedContent(BaseModel):
    """搭子请求类型特有内容"""
    id: PartnerRequestRef


class PartnerRequestEditable(BaseModel):
    """Editable fields for PartnerRequest."""
    title: Opt[str] = None
    introduction: Opt[str] = None
