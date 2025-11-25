"""贡献相关的数据模型"""

__all__ = [
    "ContributionStatus",
    "ContributeOn",
    "ContributionKeys",
    "Contribution",
    "ContributionEditable",
]

import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt

from blue_firmament.task.context import SoCommonTC
from blue_firmament.exceptions import (
    Conflict,
    Forbidden,
    InvalidStatusTransition,
    ParamsInvalid,
)
from blue_firmament.scheme import (
    BaseScheme,
    CompositeField,
    EditableScheme,
    FieldT,
    NoProxyScheme,
    field,
    field_validator,
    field_validators,
)
from blue_firmament.scheme.enum import Status

from dal import SupabaseAnonPostgrest
from account.schemas import AccountRef
from ..base import OptAbsAmount, OptRelAmount
from ..payment.base import PaymentPlatform

if typing.TYPE_CHECKING:
    from .main import SplitBill, SplitBillRef


class ContributionStatus(Status):
    """分摊记录状态"""

    PENDING = "pending"
    """等待贡献"""
    CONTRIBUTED = "contributed"
    """已贡献
    
    自动扣款暂未扣款视同已贡献
    """
    FULLY_REFUNDING = "fully_refunding"
    """全额退款中
    """
    PARTIALLY_REFUNDING = "partially_refunding"
    """部分退款中
    """
    FULLY_REFUNDED = "fully_refunded"
    """已全额退款
    """
    PARTIALLY_REFUNDED = "partially_refunded"
    """已部分退款
    """
    CLOSED = "closed"
    """正常关闭
    """
    ERROR = "error"

    def to_contributed(self):
        return self._to_target_status(ContributionStatus.CONTRIBUTED, ContributionStatus.PENDING)

    def to_refunding(self, fully: bool = False):
        return self._to_target_status(
            (
                ContributionStatus.FULLY_REFUNDING
                if fully
                else ContributionStatus.PARTIALLY_REFUNDING
            ),
            ContributionStatus.CONTRIBUTED,
        )

    def to_refunded(self):
        if self is ContributionStatus.PARTIALLY_REFUNDING:
            return ContributionStatus.PARTIALLY_REFUNDED
        elif self is ContributionStatus.FULLY_REFUNDING:
            return ContributionStatus.FULLY_REFUNDED
        raise InvalidStatusTransition(
            ContributionStatus.__name__, self.value, "(partially/fully)refunding"
        )

    def to_closed(self):
        return self._to_target_status(
            ContributionStatus.CLOSED,
            ContributionStatus.CONTRIBUTED,
        )

    def is_contributable(self):
        return self in (ContributionStatus.PENDING,)

    def is_contributed(self):
        return self in (
            ContributionStatus.CONTRIBUTED,
            ContributionStatus.FULLY_REFUNDING,
            ContributionStatus.PARTIALLY_REFUNDED,
            ContributionStatus.CLOSED,
        )


class ContributeOn(BaseScheme, proxy=False):
    """贡献渠道"""

    platform: PaymentPlatform
    """支付平台"""
    _id: str
    """支付平台ID"""


class ContributionKeys(NoProxyScheme):
    split_bill: FieldT["SplitBillRef"] = field(
        dump_flags={
            "managed",
        }
    )
    """分账账单"""
    contributor: FieldT[AccountRef] = field(
        dump_flags={
            "managed",
        }
    )
    """贡献者"""


class Contribution(
    SoCommonTC, dal=SupabaseAnonPostgrest, dal_path=("contribution", "split_bill")
):
    """贡献记录"""

    cid: CompositeField[ContributionKeys] = CompositeField(
        is_key=True,
        dump_flags={
            "managed",
        },
        vtype=ContributionKeys,
    )
    status: FieldT[ContributionStatus] = field(
        default=ContributionStatus.PENDING,
        dump_flags={
            "managed",
        },
    )
    relative_amount: OptRelAmount = OptRelAmount()
    """应贡献金额（相对值）"""
    absolute_amount: OptAbsAmount = OptAbsAmount()
    """应贡献金额（绝对值）"""
    contributed_amount: OptAbsAmount = OptAbsAmount(
        dump_flags={
            "managed",
        }
    )
    """实际贡献金额
    
    包括手续费、服务费等
    """
    auto_deducted: FieldT[Opt[bool]] = FieldT(
        default=None,
        dump_flags={
            "managed",
        },
    )
    """是否已自动扣款

    - ``None`` 代表没有开启自动扣款
    """
    contributed_on: FieldT[Opt[ContributeOn]] = FieldT(
        default=None,
        dump_flags={
            "managed",
        },
    )
    """（实际）贡献渠道（支付平台）"""

    @field_validators(relative_amount, absolute_amount, mode="assign")
    async def edit_only_when(self, value):
        """仅当分账账单为草稿时可以编辑"""
        from .main import SplitBill

        split_bill = await self._daos(SplitBill).select_one(self.cid.split_bill)
        if not split_bill.is_editable():
            raise Conflict("only editable when draft")

    @field_validator(relative_amount)
    def rel_or_abs(self, value):
        if value is not None and self.absolute_amount is None:
            return
        if value is None and self.absolute_amount is not None:
            return
        raise ParamsInvalid(
            "Rel or Abs", relative_amount=value, absolute_amount=self.absolute_amount
        )

    @field_validator(absolute_amount)
    def abs_or_rel(self, value):
        if value is not None and self.relative_amount is None:
            return
        if value is None and self.relative_amount is not None:
            return
        raise ParamsInvalid(
            "Abs or Rel", relative_amount=self.relative_amount, absolute_amount=value
        )

    @field_validator(contributed_amount)
    def validate_amount(self, value):
        """校验实付金额

        - 贡献后必须有值
        """
        if self.status.is_contributed():
            if value is None:
                raise ParamsInvalid("required after contributed", actual=value)

    @field_validator(status)
    def validate_contributed(self, value):
        """校验状态是否可以变为已贡献

        - contributed_amount 有值
        - contributed_on 有值
        """
        if value == ContributionStatus.CONTRIBUTED:
            if self.contributed_amount is None or self.contributed_on is None:
                raise ValueError("set contributed_amount and contributed_on first")

    async def get_estimate_amount(self, split_bill_amount: Opt[int] = None) -> int:
        """应付金额

        禁止在所属账单付前已付后调用该接口

        :param split_bill_amount: 分账账单金额
        """
        if self.relative_amount:
            if not split_bill_amount:
                from .main import SplitBill

                split_bill = await self._daos(SplitBill).select_one(self.cid.split_bill)
                split_bill_amount = split_bill.try_amount

            return int(split_bill_amount * self.relative_amount)
        if self.absolute_amount:
            return self.absolute_amount
        raise ValueError("impossible")

    def can_contribute(self):
        """可否贡献"""
        if not self.status.is_contributable():
            raise Conflict("not contributable")

    def is_contributed(self):
        """是否已贡献"""
        return self.status.is_contributed()

    def contributed(
        self,
        contributed_on: ContributeOn,
        contributed_amount: int,
    ):
        """标记为已贡献

        - 幂等的

        :param contributed_on: 实际贡献平台
        :param contributed_amount: 实际贡献金额

        """
        self.contributed_on = contributed_on
        self.contributed_amount = contributed_amount
        try:
            self.status = self.status.to_contributed()
        except (InvalidStatusTransition, ValueError):
            pass

    def can_refund(self):
        self.status.to_refunding()

    def refunding(self, fully: bool = False):
        """退款中"""
        self.status = self.status.to_refunding(fully)

    def refunded(self):
        """退款完成"""
        self.status = self.status.to_refunded()

    def is_abs(self) -> bool:
        return self.absolute_amount is not None

    def is_rel(self) -> bool:
        return self.relative_amount is not None


class ContributionEditable(
    EditableScheme,
    Contribution,
    default_exclude_dump_flags={
        "managed",
    },
):
    pass
