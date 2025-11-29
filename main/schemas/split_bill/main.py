"""分账模块的主要数据模型 - SQLModel Database Models."""

__all__ = [
    "SplitBillRef",
    "SplitBillType",
    "SplitBillStatus",
    "SplitBillCancelReason",
    "SplitBill",
    "SplitBillEditable",
    "SplitBillCreate",
]

import datetime
import enum
import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from utils.base import get_utc_now
from ..base import Currency
from .contribution import ContributionEditable


SplitBillRef: typing.TypeAlias = int
"""分账账单 ID"""

SPLIT_BILL_TITLE_MAX_LENGTH = 12
SPLIT_BILL_DESCRIPTION_MAX_LENGTH = 120
SPLIT_BILL_PAYEE_MAX_LENGTH = 32


class SplitBillType(enum.Enum):
    """分账账单类型"""

    POSTPAY = "postpay"
    """付后账单

    创建时，代付已经向商家支付
    """
    PREPAY = "prepay"
    """付前账单

    创建时，代付没有向商家支付，先向分摊者收集费用
    分摊者支付给代付后，代付向商家支付
    代付提交已支付的证明，系统将收集到的金额转给代付
    """


class SplitBillStatus(enum.Enum):
    """分账账单状态"""

    DRAFT = "draft"
    """草稿"""
    READY = "ready"
    """就绪（可贡献）"""
    TRANSFERRING = "transferring"
    """转移支付进行中"""
    TRANSFER_FAILED = "transfer_failed"
    """转移支付失败"""
    CLOSED = "closed"
    """正常关闭"""
    CANCELLED = "cancelled"
    """已取消"""
    REJECTED = "rejected"
    """审批驳回"""
    ERROR = "error"
    ON_PROSECUTED = "on_prosecuted"
    """人工介入"""

    def is_editable(self) -> bool:
        """是否处于可编辑状态"""
        return self in (SplitBillStatus.DRAFT,)

    def is_closed(self) -> bool:
        """是否已关闭"""
        return self in (
            SplitBillStatus.CLOSED,
            SplitBillStatus.CANCELLED,
            SplitBillStatus.REJECTED,
        )

    def is_contributable(self) -> bool:
        """是否可贡献"""
        return self in (SplitBillStatus.READY,)


class SplitBillCancelReason(enum.Enum):
    """分账账单取消原因"""

    CONTRIBUTION_EXPIRED = "contribution_expired"
    """超时未完成贡献"""
    NORMAL = "normal"
    """普通取消"""
    PAYER_DISABLED = "payer_disabled"
    """代付者无能力履行承诺的服务

    付前账单且付前账单已支付之前可用
    """
    MANUAL_OVERRIDE = "manual_override"
    """人工介入"""


class SplitBill(sqlmodel.SQLModel, table=True):
    """分账账单

    Database model for split bills.
    """
    __tablename__ = "split_bill"  # type: ignore
    __table_args__ = {"schema": "split_bill"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    type: str = sqlmodel.Field()
    """账单类型"""
    status: str = sqlmodel.Field(default=SplitBillStatus.DRAFT.value)
    """账单状态"""
    created_by: str = sqlmodel.Field()
    """创建者"""
    created_at: datetime.datetime = sqlmodel.Field(default_factory=get_utc_now)
    """创建时间"""
    partner_request: Opt[int] = sqlmodel.Field(default=None)
    """所属搭子请求"""
    sub_split_bill: Opt[int] = sqlmodel.Field(default=None)
    """补充的分账账单"""
    cancelled_for: Opt[str] = sqlmodel.Field(default=None)
    """取消原因

    在 Status:Cancelled 时才有值
    """
    title: Opt[str] = sqlmodel.Field(default=None)
    """账单标题 (max: 12)"""
    description: Opt[str] = sqlmodel.Field(default=None)
    """账单描述 (max: 120)"""
    details: Opt[str] = sqlmodel.Field(default=None)
    """账单详情 (JSON)"""
    proof: Opt[str] = sqlmodel.Field(default=None)
    """证据 (JSON)"""
    currency: str = sqlmodel.Field(default=Currency.CNY.value)
    """币种"""
    amount: Opt[int] = sqlmodel.Field(default=None)
    """账单（实付）金额

    - 付后账单从 Status:Draft 开始有值
    - 付前账单从 Status:PrepayPaid 开始有值
    """
    estimate_amount: Opt[int] = sqlmodel.Field(default=None)
    """预估实付金额

    - 付前账单有值
    """
    payee: Opt[str] = sqlmodel.Field(default=None)
    """收款方（商家）"""
    payer: str = sqlmodel.Field()
    """付款方（代付者）"""
    paid_at: Opt[datetime.datetime] = sqlmodel.Field(default=None)
    """实付时间"""
    contribute_before: Opt[datetime.datetime] = sqlmodel.Field(default=None)
    """贡献截止时间"""

    def get_type(self) -> SplitBillType:
        """Get type as enum."""
        return SplitBillType(self.type)

    def set_type(self, bill_type: SplitBillType) -> None:
        """Set type from enum."""
        self.type = bill_type.value

    def get_status(self) -> SplitBillStatus:
        """Get status as enum."""
        return SplitBillStatus(self.status)

    def set_status(self, status: SplitBillStatus) -> None:
        """Set status from enum."""
        self.status = status.value

    def is_editable(self) -> bool:
        """是否处于可编辑状态"""
        return self.get_status().is_editable()

    def is_contributable(self) -> bool:
        """是否可贡献"""
        return self.get_status().is_contributable()

    @property
    def try_amount(self) -> int:
        """实付金额或预估金额"""
        return self.amount or self.estimate_amount or 0

    def is_prepay_paid(self) -> bool:
        """是否付前已付"""
        return self.get_type() is SplitBillType.PREPAY and self.amount is not None


class SplitBillEditable(BaseModel):
    """Editable fields for SplitBill."""
    title: Opt[str] = None
    description: Opt[str] = None
    details: Opt[str] = None  # JSON string
    proof: Opt[str] = None  # JSON string
    payee: Opt[str] = None
    amount: Opt[int] = None
    estimate_amount: Opt[int] = None
    partner_request: Opt[int] = None
    contribute_before: Opt[datetime.datetime] = None


class SplitBillCreate(BaseModel):
    """Create model for SplitBill."""
    type: SplitBillType
    created_by: str
    payer: str
    title: Opt[str] = None
    description: Opt[str] = None
    details: Opt[str] = None
    proof: Opt[str] = None
    currency: Currency = Currency.CNY
    amount: Opt[int] = None
    estimate_amount: Opt[int] = None
    payee: Opt[str] = None
    partner_request: Opt[int] = None
    contribute_before: Opt[datetime.datetime] = None
    contributions: list[ContributionEditable] = []
    """贡献记录列表"""
