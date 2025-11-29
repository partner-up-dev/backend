"""贡献相关的数据模型 - SQLModel Database Models."""

__all__ = [
    "ContributionStatus",
    "ContributeOn",
    "ContributionKeys",
    "Contribution",
    "ContributionEditable",
]

import enum
import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from ..payment.base import PaymentPlatform

if typing.TYPE_CHECKING:
    pass


class ContributionStatus(enum.Enum):
    """分摊记录状态"""

    PENDING = "pending"
    """等待贡献"""
    CONTRIBUTED = "contributed"
    """已贡献

    自动扣款暂未扣款视同已贡献
    """
    FULLY_REFUNDING = "fully_refunding"
    """全额退款中"""
    PARTIALLY_REFUNDING = "partially_refunding"
    """部分退款中"""
    FULLY_REFUNDED = "fully_refunded"
    """已全额退款"""
    PARTIALLY_REFUNDED = "partially_refunded"
    """已部分退款"""
    CLOSED = "closed"
    """正常关闭"""
    ERROR = "error"

    def is_contributable(self) -> bool:
        """是否可贡献"""
        return self in (ContributionStatus.PENDING,)

    def is_contributed(self) -> bool:
        """是否已贡献"""
        return self in (
            ContributionStatus.CONTRIBUTED,
            ContributionStatus.FULLY_REFUNDING,
            ContributionStatus.PARTIALLY_REFUNDED,
            ContributionStatus.CLOSED,
        )


class ContributeOn(BaseModel):
    """贡献渠道"""

    platform: PaymentPlatform
    """支付平台"""
    id: str
    """支付平台ID"""


class ContributionKeys(BaseModel):
    """Contribution composite key."""
    split_bill: int
    """分账账单ID"""
    contributor: str
    """贡献者ID"""


class Contribution(sqlmodel.SQLModel, table=True):
    """贡献记录

    Database model for contributions.
    """
    __tablename__ = "contribution"  # type: ignore
    __table_args__ = {"schema": "split_bill"}

    # Composite primary key
    split_bill: int = sqlmodel.Field(primary_key=True)
    """分账账单"""
    contributor: str = sqlmodel.Field(primary_key=True)
    """贡献者"""
    status: str = sqlmodel.Field(default=ContributionStatus.PENDING.value)
    relative_amount: Opt[float] = sqlmodel.Field(default=None)
    """应贡献金额（相对值）"""
    absolute_amount: Opt[int] = sqlmodel.Field(default=None)
    """应贡献金额（绝对值）"""
    contributed_amount: Opt[int] = sqlmodel.Field(default=None)
    """实际贡献金额

    包括手续费、服务费等
    """
    auto_deducted: Opt[bool] = sqlmodel.Field(default=None)
    """是否已自动扣款

    - ``None`` 代表没有开启自动扣款
    """
    contributed_on_platform: Opt[str] = sqlmodel.Field(default=None)
    """（实际）贡献渠道（支付平台）"""
    contributed_on_id: Opt[str] = sqlmodel.Field(default=None)
    """（实际）贡献渠道ID"""

    def get_status(self) -> ContributionStatus:
        """Get status as enum."""
        return ContributionStatus(self.status)

    def set_status(self, status: ContributionStatus) -> None:
        """Set status from enum."""
        self.status = status.value

    def is_contributed(self) -> bool:
        """是否已贡献"""
        return self.get_status().is_contributed()

    def is_contributable(self) -> bool:
        """是否可贡献"""
        return self.get_status().is_contributable()

    def get_contributed_on(self) -> Opt[ContributeOn]:
        """Get contribution payment platform info."""
        if self.contributed_on_platform and self.contributed_on_id:
            return ContributeOn(
                platform=PaymentPlatform(self.contributed_on_platform),
                id=self.contributed_on_id
            )
        return None

    def set_contributed_on(self, contribute_on: ContributeOn) -> None:
        """Set contribution payment platform info."""
        self.contributed_on_platform = contribute_on.platform.value
        self.contributed_on_id = contribute_on.id

    def is_abs(self) -> bool:
        """是否为绝对值"""
        return self.absolute_amount is not None

    def is_rel(self) -> bool:
        """是否为相对值"""
        return self.relative_amount is not None

    def get_estimate_amount(self, split_bill_amount: int) -> int:
        """计算应付金额

        :param split_bill_amount: 分账账单金额
        """
        if self.relative_amount is not None:
            return int(split_bill_amount * self.relative_amount)
        if self.absolute_amount is not None:
            return self.absolute_amount
        raise ValueError(
            f"Either relative_amount or absolute_amount must be set, "
            f"got relative={self.relative_amount}, absolute={self.absolute_amount}"
        )


class ContributionEditable(BaseModel):
    """Editable fields for Contribution."""
    relative_amount: Opt[float] = None
    """应贡献金额（相对值）"""
    absolute_amount: Opt[int] = None
    """应贡献金额（绝对值）"""


class ContributionCreate(BaseModel):
    """Create model for Contribution."""
    split_bill: int
    contributor: str
    relative_amount: Opt[float] = None
    absolute_amount: Opt[int] = None
