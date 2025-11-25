"""分账模块的主要数据模型"""

import datetime
import enum
import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt

from blue_firmament._types import Undefined, _undefined
from blue_firmament.exceptions import (
    Conflict,
    InvalidStatusTransition,
    ParamsInvalid,
)
from blue_firmament.scheme import (
    BusinessScheme,
    EditableScheme,
    FieldT,
    OptionalConveter,
    StrConverter,
    field,
    field_validator,
    field_validators,
)
from blue_firmament.scheme.enum import Status
from blue_firmament.scheme.field import Field
from blue_firmament.task.context import SoCommonTC
from blue_firmament.utils.datetime_ import get_datetimez

from dal import SupabaseAnonPostgrest
from account.schemas import AccountRef
from ..base import Currency, Navigation, OptAbsAmount
from ..partner_request.base import PartnerRequest, PartnerRequestRef
from .contribution import Contribution, ContributionEditable

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


class SplitBillStatus(Status):
    """分账账单状态"""

    DRAFT = "draft"
    """草稿"""
    READY = "ready"
    """就绪（可贡献）"""
    TRANSFERRING = "transferring"
    """转移支付进行中
    """
    TRANSFER_FAILED = "transfer_failed"
    """转移支付失败
    """
    CLOSED = "closed"
    """正常关闭
    """
    CANCELLED = "cancelled"
    """已取消"""
    REJECTED = "rejected"
    """审批驳回"""
    ERROR = "error"
    ON_PROSECUTED = "on_prosecuted"
    """人工介入"""

    def is_editable(self):
        """是否处于可编辑状态"""
        return self in (SplitBillStatus.DRAFT,)

    def is_closed(self):
        """是否已关闭"""
        return self in (
            SplitBillStatus.CLOSED,
            SplitBillStatus.CANCELLED,
            SplitBillStatus.REJECTED,
        )

    def is_contributable(self):
        return self in (SplitBillStatus.READY,)

    def to_ready(self):
        return self._to_target_status(
            SplitBillStatus.READY, SplitBillStatus.REJECTED, SplitBillStatus.DRAFT
        )

    def to_transferring(self):
        return self._to_target_status(SplitBillStatus.TRANSFERRING, SplitBillStatus.READY)

    def to_transfer_failed(self):
        return self._to_target_status(
            SplitBillStatus.TRANSFER_FAILED, SplitBillStatus.TRANSFERRING
        )

    def to_rejected(self):
        return self._to_target_status(
            SplitBillStatus.REJECTED,
            SplitBillStatus.READY,
        )

    def to_closed(self):
        return self._to_target_status(SplitBillStatus.CLOSED, SplitBillStatus.TRANSFERRING)

    def to_cancelled(self):
        return self._to_target_status(SplitBillStatus.CANCELLED, SplitBillStatus.READY)


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


type SplitBillDetailsT = typing.List[tuple[str, int]]


class SplitBillDetails(Field[SplitBillDetailsT]):
    """账单详情"""

    def __init__(self, **kwargs):
        kwargs["default_factory"] = list
        super().__init__(**kwargs)


class SplitBillTitle(Field[Opt[str]]):
    """账单标题"""

    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(
            tp_converter=StrConverter(max=SPLIT_BILL_TITLE_MAX_LENGTH)
        )
        super().__init__(**kwargs)


class SplitBillDescription(Field[Opt[str]]):
    """账单描述"""

    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(
            tp_converter=StrConverter(max=SPLIT_BILL_DESCRIPTION_MAX_LENGTH)
        )
        super().__init__(**kwargs)


class SplitBillPayee(Field[str]):
    """账单收款方"""

    def __init__(self, **kwargs):
        kwargs["converter"] = StrConverter(max=SPLIT_BILL_PAYEE_MAX_LENGTH)
        super().__init__(**kwargs)


class SplitBillContributors(Field[set[AccountRef]]):
    """账单贡献者列表"""

    def __init__(self, **kwargs):
        kwargs["default_factory"] = set
        super().__init__(**kwargs)


SplitBillRef = typing.NewType("SplitBillRef", int)
"""分账账单 ID"""
type SplitBillProofT = Opt[str | Navigation | SplitBillRef]


class SplitBill(
    BusinessScheme[SplitBillRef],
    SoCommonTC,
    key_type=SplitBillRef,
    dal=SupabaseAnonPostgrest,
    dal_path=("split_bill", "split_bill"),
):
    """分账账单"""

    type: SplitBillType
    status: FieldT[SplitBillStatus] = field(
        default=SplitBillStatus.DRAFT,
        dump_flags={
            "managed",
        },
    )
    created_by: FieldT[AccountRef] = field(
        dump_flags={
            "managed",
        }
    )
    created_at: FieldT[datetime.datetime] = field(
        default_factory=get_datetimez,
        dump_flags={
            "managed",
        },
    )
    partner_request: FieldT[Opt[PartnerRequestRef]] = field(default=None)
    """所属搭子请求
    """
    sub_split_bill: FieldT[Opt[SplitBillRef]] = field(
        default=None,
        dump_flags={
            "managed",
        },
    )
    """补充的分账账单
    """
    cancelled_for: FieldT[Opt[SplitBillCancelReason]] = field(
        default=None,
        dump_flags={
            "managed",
        },
    )
    """取消原因
    
    在 Status:Cancelled 时才有值
    """
    title: SplitBillTitle = SplitBillTitle()
    description: SplitBillDescription = SplitBillDescription()
    details: SplitBillDetails = SplitBillDetails()
    """账单详情"""
    proof: FieldT[SplitBillProofT] = field(default=None)
    """证据"""
    currency: Currency = Currency.CNY
    """币种
    """
    amount: OptAbsAmount = OptAbsAmount()
    """账单（实付）金额

    - 付后账单从 Status:Draft 开始有值
    - 付前账单从 Status:PrepayPaid 开始有值
    """
    estimate_amount: OptAbsAmount = OptAbsAmount()
    """预估实付金额

    - 付前账单有值
    """
    payee: SplitBillPayee = SplitBillPayee()
    """收款方（商家）
    """
    payer: FieldT[AccountRef] = field()
    """付款方（代付者）
    """
    paid_at: FieldT[Opt[datetime.datetime]] = field(default=None)
    """实付时间
    """
    contribute_before: FieldT[Opt[datetime.datetime]] = field(default=None)
    """贡献截止时间
    """

    @field_validators(
        title,
        description,
        payer,
        amount,
        estimate_amount,
        paid_at,
        partner_request,
        contribute_before,
        mode="assign",
    )
    def eit_only_when_draft(self, value):
        if not self.is_editable():
            raise Conflict("not editable now")

    @field_validators(payee, proof, details, mode="assign")
    def edit_only_then_prepaypaid_or_draft(self, value):
        if (
            not self.is_editable()
            and not self.is_prepay_paid()  # FIXME 无法保证付前已付之后不继续编辑？（仔细想想）
        ):
            raise Conflict("not editable now")

    @field_validator(estimate_amount)
    def prepay_estimate_not_null(self, value):
        """
        付前账单必须有预估实付金额
        """
        if self.type == SplitBillType.PREPAY and value is None:
            raise ParamsInvalid("required for prepay", estimate=value)

    @field_validator(amount)
    def validate_amount(self, value):
        """校验实付金额

        - 付后账单必须有
        """
        if self.type == SplitBillType.POSTPAY and value is None:
            raise ParamsInvalid("required for postpay", actual=value)

    async def _validate_contributions(self):
        """校验应贡献额总和是否等于账单(预估)总额

        仅在切换为就绪状态时检查

        :raise ValueError: 不等于
        """
        # TODO NotFound will be ignored if requires at least num
        contributions: typing.Tuple[Contribution] = await self._daos(Contribution).select(
            Contribution.cid.vtype.split_bill.equals(self._id)
        )

        split_bill_estimate_total = self.try_amount
        total_estimate_contribution: int = 0
        for contribution in contributions:
            total_estimate_contribution += await contribution.get_estimate_amount(
                split_bill_estimate_total
            )

        if total_estimate_contribution != split_bill_estimate_total:
            raise ParamsInvalid(
                "contribution_estimate_total should be same as estimate_total",
                total_estimate_contribution=total_estimate_contribution,
                estimate_total=split_bill_estimate_total,
            )

    @field_validator(status)
    async def validate_ready(self, value: SplitBillStatus):
        """检查是否可以变更状态为就绪

        - 有搭子请求，且搭子请求在可能产生账单的状态中
        - 贡献额总和等于账单总额
        """
        if value == SplitBillStatus.READY:
            await self._validate_contributions()

            if self.partner_request is None:
                raise ParamsInvalid("PR is required to submit a split bill")

            pr = await self._daos(PartnerRequest).select_one(self.partner_request)
            if not pr.is_bill_submittable():
                raise Conflict("PR can't accept bill now", partner_request=self.partner_request)

    @field_validator(status)
    async def validate_cancelled(self, value):
        """检查是否可变更状态为已取消"""
        if value == SplitBillStatus.CANCELLED:
            if self.type is SplitBillType.POSTPAY:
                if self.status not in (SplitBillStatus.DRAFT,):
                    raise InvalidStatusTransition("SplitBillStatus", self.status, value)
            elif self.type is SplitBillType.PREPAY:
                if await self.is_contributed():
                    raise InvalidStatusTransition("SplitBillStatus", self.status, value)
            if self.cancelled_for is None:
                raise ValueError("cancelled_for is required")

    async def get_stakeholders(self) -> tuple[AccountRef, ...]:
        """利益相关者"""
        return (self.payer, *(await self.get_contributors()))

    def is_editable(self) -> bool:
        return self.status.is_editable()

    def is_contributable(self) -> bool:
        return self.status.is_contributable()

    async def is_contributed(self) -> bool:
        """是否全部已贡献"""
        contributions = await self._daos(Contribution).select(
            Contribution.cid._sub.split_bill.equals(self._id),
        )
        return all(contribution.is_contributed() for contribution in contributions)

    @property
    def try_amount(self) -> int:
        """实付金额或预估金额"""
        return typing.cast(int, self.amount or self.estimate_amount)

    def is_prepay_paid(self) -> bool:
        """是否付前已付"""
        return self.type is SplitBillType.PREPAY and self.amount is not None

    async def get_contributed_amount(self) -> int:
        """获取已贡献额"""
        contributions = await self.get_contributions()
        return sum(contribution.contributed_amount or 0 for contribution in contributions)

    async def get_oversupplement_amount(self) -> int:
        """获取多贡献的金额"""
        if self.amount is None:
            raise ParamsInvalid("split_bill amount is None")
        return (await self.get_contributed_amount()) - self.amount

    def submit(self):
        """提交"""
        self.status = self.status.to_ready()

    def can_submit(self):
        """可否提交"""
        self.status.to_ready()

    def reject(self):
        """驳回

        :raise Conflict: 付前已付之后
        """
        if self.is_prepay_paid():
            raise Conflict("prepay paid")
        self.status = self.status.to_rejected()

    def can_contribute(self):
        """可否贡献

        :raise Conflict: 不可贡献
        """
        if not self.status.is_contributable():
            raise Conflict("not contributable")

    async def get_contributions(self) -> typing.Tuple[Contribution, ...]:
        """获取贡献记录"""
        return await self._daos(Contribution).select(
            Contribution.cid.vtype.split_bill.equals(self._id)
        )

    async def get_contributors(self) -> tuple[AccountRef, ...]:
        """获取贡献者列表"""
        return await self._daos(Contribution).select_field(
            Contribution.cid._sub.contributor, Contribution.cid._sub.split_bill.equals(self._id)
        )

    async def prepay_paid(
        self,
        amount: int,
        details: Undefined | SplitBillDetailsT = _undefined,
        payee: Undefined | str = _undefined,
        proof: Undefined | SplitBillProofT = _undefined,
    ):
        """付前账单已实付

        :raise Conflict: 已付；未全部已贡献
        """
        if self.is_prepay_paid():
            raise Conflict("Already prepay paid")
        if not (await self.is_contributed()):
            raise Conflict("Cannot pay prepay before contributed")

        self.amount = amount
        self.paid_at = get_datetimez()

        if details is not _undefined:
            self.details = details
        if payee is not _undefined:
            self.payee = payee
        if proof is not _undefined:
            self.proof = proof

    def cancel(self, reason: SplitBillCancelReason):
        self.cancelled_for = reason
        self.status = self.status.to_cancelled()

    async def can_transfer(self):
        """
        :raise Conflict: 付前未付；未过实付24h；非全部已贡献
        """
        self.status.to_transferring()  # 确保没有未解决的付前已付异议

        if self.type is SplitBillType.PREPAY:
            if not self.is_prepay_paid:
                raise Conflict("payer not paid yet")
            if not self.paid_at:
                raise ParamsInvalid("paid_at is None")
            if get_datetimez() - self.paid_at <= datetime.timedelta(hours=24):
                raise Conflict("not after paid 24h yet")
            return  # 付前已付必然全部已贡献

        if not (await self.is_contributed()):
            raise Conflict("not all contributed yet")

    def transfer_initiated(self):
        self.status = self.status.to_transferring()

    def transfer_failed(self):
        self.status = self.status.to_transfer_failed()

    def transferred(self):
        self.status = self.status.to_closed()

    def close(self):
        self.status = self.status.to_closed()


class SplitBillForPatch(
    EditableScheme,
    SplitBill,
    default_exclude_dump_flags={
        "managed",
    },
):
    pass


class SplitBillForCreate(SplitBillForPatch):
    contributions: FieldT[list[ContributionEditable]] = field(is_partial=False)
    """贡献记录列表"""
