"""贡献记录管理器"""

import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt
from blue_firmament import listen_to
from blue_firmament.exceptions import InvalidStatusTransition, ParamsInvalid
from blue_firmament.manager import CommonManager
from blue_firmament.manager.common import PresetHandlerConfig
from blue_firmament.transport import Method
from blue_firmament.utils import encryption
from account.schemas import AccountRef
from ...schemas.payment.base import PaymentPlatform
from ...schemas.split_bill import (
    ContributeOn,
    Contribution,
    ContributionEditable,
    ContributionKeys,
    ContributionStatus,
    SplitBillRef,
)

from ..payment import PAYMENT_GATEWAY
from .main import SplitBillManager
from settings.transport import get_setting as get_transport_setting
from blue_firmament.task import TaskStatus


class ContributionManager(
    CommonManager[Contribution, ContributionKeys],
    scheme_cls=Contribution,
    path_prefix=SplitBillManager.__path_prefix__ + "/{split_bill_id}/contribution",
    manager_name="contribution",
    preset_handler_config=PresetHandlerConfig(
        get=True,
        put=True,
        delete=True,
        sup_path="/{contributor}",
        key_fields={
            "split_bill_id": ContributionKeys.split_bill,
            "contributor": ContributionKeys.contributor,
        },
        editable=ContributionEditable,
    ),
):
    @listen_to(Method.POST, "")
    async def create(self, split_bill_id: SplitBillRef, body: ContributionEditable):
        """创建贡献记录"""
        await SplitBillManager(self).must_be_editable(split_bill_id)

        return await self._dao.insert(
            Contribution(
                _task_context=self,
                cid=ContributionKeys(split_bill=split_bill_id, contributor=body.cid.contributor),
                **body.dump_to_dict(),
            )
        )

    def _get_contribution_tran_id(
        self,
        split_bill_id: SplitBillRef,
        contribute_on: ContributeOn,
        contributor: AccountRef,
        type_: Lit["payment", "refund"],
    ) -> str:
        """贡献支付交易订单 ID

        ``md5(<contribute_on>-<split_bill_id>-<contributor>-<op_type>)``

        :param type_: 类型

            - "payment": 贡献收款
            - "refund": 退款
        :returns: 32 位的小写字符串
        """
        return encryption.md5(f"{contribute_on}-{split_bill_id}-{contributor}-{type_}")

    def _get_contribution_callback_url(
        self, contribute_on: PaymentPlatform, split_bill_id: SplitBillRef, contributor
    ) -> str:
        """获取贡献支付订单回调地址

        `接口 <https://app.apifox.com/link/project/4406548/apis/api-215664917>`_

        :returns: 回调地址 （256 字符内）
        """
        return (
            f"https://{get_transport_setting().http_real_host}/split_bill/{split_bill_id}"
            f"/contribution/{contributor}/contributed/{contribute_on}"
        )

    SERVICE_RATE_CONFIG: list[tuple[int, float]] = [
        (50, 0.006),
        (100, 0.008),
        (500, 0.01),
    ]

    @classmethod
    def _get_service_fee(cls, amount: int) -> int:
        """计算服务费"""
        for i in range(len(cls.SERVICE_RATE_CONFIG)):
            if amount > cls.SERVICE_RATE_CONFIG[i][0]:
                continue
            return int(round(amount * cls.SERVICE_RATE_CONFIG[i][1], 0))

        return int(round(amount * cls.SERVICE_RATE_CONFIG[-1][1], 0))

    @listen_to(Method.POST, "/contribute")
    async def contribute(
        self,
        split_bill_id: SplitBillRef,
        payment_platform: PaymentPlatform,
        auto_deduction: bool = False,
    ):
        """请求贡献"""
        contributor = AccountRef(self._operator.id)
        sbm = SplitBillManager(self)
        split_bill = await sbm.get(_id=split_bill_id)
        contribution = await self._get_scheme(
            ContributionKeys(split_bill=split_bill_id, contributor=contributor)
        )

        await sbm.must_be_contributable(split_bill_id)
        contribution.can_contribute()

        # 1. prepare data
        payment_manager = PAYMENT_GATEWAY[payment_platform].get(self)
        payment_id = self._get_contribution_tran_id(
            split_bill_id=split_bill_id,
            contribute_on=ContributeOn(platform=payment_platform, _id=payment_manager._id),
            contributor=contributor,
            type_="payment",
        )
        orginal_amount = await contribution.get_estimate_amount(
            split_bill_amount=split_bill.try_amount
        )
        amount: int = (
            orginal_amount
            + payment_manager.get_fee(orginal_amount)
            + self._get_service_fee(orginal_amount)
        )

        # 2. request payment
        # TODO 支持自动扣款
        res = payment_manager.collect(
            _id=payment_id,
            amount=amount,
            currency=split_bill.currency,
            description=f"Contributor {contributor}'s contribution to SplitBill #{split_bill_id}",  # TODO i18n
            payer=contributor,
            callback_url=self._get_contribution_callback_url(
                split_bill_id=split_bill_id,
                contributor=contributor,
                contribute_on=payment_platform,
            ),
        )

        self._task_result.status = TaskStatus.CREATED
        return res

    @listen_to(Method.GET, "/is_contributed")
    async def check_is_contributed(
        self,
        split_bill_id: SplitBillRef,
        payment_platform: PaymentPlatform,
    ) -> Contribution:
        """检查贡献结果

        - 幂等
        """
        # 1. 获取贡献订单
        contributor = AccountRef(self._operator.id)
        payment_manager = PAYMENT_GATEWAY[payment_platform].get(self)
        contribute_on = ContributeOn(platform=payment_platform, _id=payment_manager._id)
        trans_id = self._get_contribution_tran_id(
            split_bill_id=split_bill_id,
            contribute_on=contribute_on,
            contributor=contributor,
            type_="payment",
        )
        transaction = payment_manager.get_collect_transaction(trans_id)

        # 2. 检查是否成功
        if transaction.is_success():
            await self._contributed(
                split_bill_id=split_bill_id,
                contributor=contributor,
                contribute_on=contribute_on,
                amount=transaction.amount,
            )
        elif transaction.is_failed():
            self._logger.error("Contribution payment failed")
        else:
            self._logger.warning("Contribution not successed yet")

        return await self._get_scheme(
            ContributionKeys(split_bill=split_bill_id, contributor=contributor)
        )

    async def is_contributed(
        self,
        split_bill_id: SplitBillRef,
        contributor: AccountRef,
    ) -> bool:
        """是否已贡献"""
        return (
            await self._get_scheme(
                ContributionKeys(split_bill=split_bill_id, contributor=contributor)
            )
        ).is_contributed()

    @listen_to(
        Method.POST, "/{contributor}/payment_callback/{payment_platform}/{payment_platform_id}"
    )
    async def on_contribution_callback(
        self,
        split_bill_id: SplitBillRef,
        contributor: AccountRef,
        payment_platform: PaymentPlatform,
        payment_platform_id: str,
    ):
        """处理贡献回调"""
        pm = PAYMENT_GATEWAY[payment_platform].get_by_id(payment_platform_id, self)
        transaction = pm.resolve_collect_callback(self._task)

        if transaction.is_success():
            await self._contributed(
                split_bill_id=split_bill_id,
                contributor=contributor,
                contribute_on=ContributeOn(platform=payment_platform, _id=payment_platform_id),
                amount=transaction.amount,
            )
        elif transaction.is_failed():
            self._logger.error("Contribution payment failed")
        else:
            self._logger.warning("Contribution not successed yet")

    async def _contributed(
        self,
        split_bill_id: SplitBillRef,
        contributor: AccountRef,
        contribute_on: ContributeOn,
        amount: int,
    ):
        """贡献成功（幂等）"""
        contribution = await self._get_scheme(
            ContributionKeys(split_bill=split_bill_id, contributor=contributor)
        )

        contribution.contributed(contributed_on=contribute_on, contributed_amount=amount)
        await self._update_scheme(contribution)

        await SplitBillManager(self).on_a_contribution_contributed(split_bill_id=split_bill_id)

    def _get_refund_callback_url(
        self, split_bill_id: SplitBillRef, contributor: AccountRef, contribute_on: ContributeOn
    ) -> str:
        """获取贡献退款回调地址

        ``SERVER_HOST + /split_bill/{split_bill_id}/refunded/{payment_platform}``
        """
        return f"https://{get_transport_setting().http_real_host}/split_bill/{
            split_bill_id
        }/contribution/{contributor}/refunded/{contribute_on.platform.value}/{contribute_on._id}"

    async def refund(
        self,
        split_bill_id: SplitBillRef,
        contributor: Opt[AccountRef] = None,
        full: bool = False,
        reason: Opt[str] = "refund oversupplement",
    ) -> None:
        """退款

        - 只有已贡献后，转账前可以退款，否则跳过

        :param contributor: 贡献者

            如果不提供，则退还该分账账单下所有的贡献记录
        :param full:
            是否全额退款（包括手续费）

            在非全额退款的情况下，如果贡献记录采用绝对模式，则不会发生退款
        :param reason: 退款原因，默认为多退
        """
        split_bill = await SplitBillManager(self).get(_id=split_bill_id)

        contributions: tuple[Contribution, ...]
        if not contributor:
            contributions = await self._dao.select(
                Contribution.cid._sub.split_bill.equals(split_bill_id)
            )
        else:
            contributions = (
                await self._get_scheme(
                    ContributionKeys(split_bill=split_bill_id, contributor=contributor)
                ),
            )

        for contribution in contributions:
            try:
                contribution.can_refund()
            except InvalidStatusTransition:
                self._logger.warning("cannot refund the contribution", contribution=contribution)
                continue

            # 2. calculate amount to refund
            amount: int
            if not full:
                if contribution.relative_amount is None:
                    self._logger.warning("Abs contribution is not partially refundable")
                    continue

                oversupplement = await split_bill.get_oversupplement_amount()
                if oversupplement <= 0:
                    raise ParamsInvalid("oversupplement is 0")

                amount = int(round(oversupplement * contribution.relative_amount, 0))
            else:
                if contribution.contributed_amount is None:
                    raise ParamsInvalid("contributed_amount is None")
                amount = contribution.contributed_amount

            # 3. refund TODO 支持自动扣款退款
            if not contribution.contributed_on:
                raise ParamsInvalid("contributed_on is None")

            contribution_trans_id = self._get_contribution_tran_id(
                split_bill_id=split_bill_id,
                contribute_on=contribution.contributed_on,
                contributor=contribution.cid.contributor,
                type_="payment",
            )
            refund_id = self._get_contribution_tran_id(
                split_bill_id=split_bill_id,
                contribute_on=contribution.contributed_on,
                contributor=contribution.cid.contributor,
                type_="refund",
            )
            PAYMENT_GATEWAY[contribution.contributed_on.platform].get_by_id(
                contribution.contributed_on._id, self
            ).refund(
                _id=refund_id,
                collect_id=contribution_trans_id,
                amount=amount,
                currency=split_bill.currency,
                callback_url=self._get_refund_callback_url(
                    split_bill_id=split_bill_id,
                    contributor=contribution.cid.contributor,
                    contribute_on=contribution.contributed_on,
                ),
                reason=reason,
            )

            contribution.refunding(fully=full)
            contribution = await self._update_scheme(contribution)

            await self._emit(
                "split_bill.contribution.refund_initiated",
                {"split_bill_id": split_bill._id, "contributor": contribution.cid.contributor},
                without_prefix=True,
            )

    @listen_to(
        Method.POST, "/{contributor}/refund_callback/{payment_platform}/{payment_platform_id}"
    )
    async def on_refund_callback(
        self,
        split_bill_id: SplitBillRef,
        contributor: AccountRef,
        payment_platform: PaymentPlatform,
        payment_platform_id: str,
    ):
        """处理退款回调（幂等）"""
        pm = PAYMENT_GATEWAY[payment_platform].get_by_id(payment_platform_id, self)
        transaction = pm.resolve_refund_callback(self._task)

        contribution = await self._get_scheme(
            ContributionKeys(split_bill=split_bill_id, contributor=contributor)
        )
        if transaction.is_success():
            contribution.refunded()
        elif transaction.is_failed():
            self._logger.error("Contribution refund failed")
            contribution.status = ContributionStatus.ERROR
        else:
            self._logger.warning("Contribution refund not successed yet")

        await self._update_scheme(contribution)
