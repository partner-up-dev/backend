"""分账模块管理器"""

import datetime
import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt

from blue_firmament import listen_to
from blue_firmament._types import _undefined
from blue_firmament.exceptions import Conflict, Forbidden, ParamsInvalid
from blue_firmament.manager import CommonManager
from blue_firmament.manager.common import PresetHandlerConfig
from blue_firmament.scheme import StrConverter
from blue_firmament.task import TaskStatus
from blue_firmament.transport import Method
from blue_firmament.utils import encryption
from blue_firmament.utils.datetime_ import get_datetimez
from account.schemas import AccountRef
from ...schemas.payment.base import PaymentPlatform, TransferScene
from ...schemas.split_bill import (
    Contribution,
    ContributionEditable,
    ContributionKeys,
    SplitBill,
    SplitBillCancelReason,
    SplitBillForCreate,
    SplitBillForPatch,
    SplitBillRef,
    SplitBillStatus,
    SplitBillType,
)
from ...schemas.split_bill.response import (
    SplitBillV2CreateRes,
    SplitBillV1InitiateTransferRes,
)
from ..payment import PAYMENT_GATEWAY
from settings.transport import get_setting as get_transport_setting


class SplitBillManager(
    CommonManager[SplitBill, SplitBillRef],
    scheme_cls=SplitBill,
    path_prefix="split_bill",
    manager_name="split_bill",
    preset_handler_config=PresetHandlerConfig(get=True, put=True, editable=SplitBillForPatch),
):
    async def must_be_editable(self, split_bill_id: Opt[SplitBillRef] = None) -> None:
        """
        :raise Conflict: 账单不可编辑
        """
        split_bill = await self._get_scheme(split_bill_id)
        if not split_bill.is_editable():
            raise Conflict("the split bill is not editable")

    async def must_be_contributable(self, split_bill_id: Opt[SplitBillRef] = None) -> None:
        """
        :raise Conflict: 账单不可贡献
        """
        split_bill = await self._get_scheme(split_bill_id)
        if not split_bill.is_contributable():
            raise Conflict("the split bill is not contributable")

    async def must_be_created_by(self, split_bill_id: Opt[SplitBillRef] = None) -> None:
        """
        :raise Forbidden: 操作者不是账单的创建者
        """
        split_bill = await self._get_scheme(split_bill_id)
        if split_bill.created_by != self._operator.id:
            raise Forbidden("must be created_by of the split bill")

    async def must_be_stakeholder(
        self, split_bill_id: Opt[SplitBillRef] = None
    ) -> Lit["contributor"] | Lit["payer"]:
        """
        :raise Forbidden: 操作者不是账单的利益相关者
        :returns: stakeholder type
        """
        split_bill = await self._get_scheme(split_bill_id)
        if self._operator.id == split_bill.payer:
            return "payer"

        try:
            await self.must_be_contributor(split_bill_id)
        except Forbidden:
            raise Forbidden("must be a stakeholder of the split bill")
        else:
            return "contributor"

    async def must_be_contributor(self, split_bill_id: Opt[SplitBillRef] = None):
        """
        :raise Forbidden: 操作者不是账单的贡献者
        """
        split_bill = await self._get_scheme(split_bill_id)
        if self._operator.id not in (await split_bill.get_contributors()):
            raise Forbidden("must be a contributor of the split bill")

    @listen_to(Method.GET, "/mine")
    async def get_mine(self, account_id: AccountRef) -> typing.Iterable[SplitBillRef]:
        """获取我的分账账单"""
        account_id = account_id or AccountRef(self._operator.id)

        # 1. 获得作为创建者的账单
        created_bills = await self._dao.select_field(
            SplitBill._id,
            SplitBill.created_by.equals(account_id),
        )

        # 2. 获取不是创建者但是分摊者的账单
        non_created_bills = await self._daos(Contribution).select_field(
            Contribution.cid._sub.split_bill,
            *Contribution.cid._sub.split_bill.not_in_(created_bills),
            Contribution.cid._sub.contributor.equals(account_id),
        )

        return created_bills + non_created_bills

    @listen_to(Method.POST, "")
    async def create(
        self, body: SplitBillForCreate, submit: bool = False
    ) -> SplitBillV2CreateRes:
        """创建分账账单

        :param submit: 是否直接提交

        TODO 事务性
        """
        if body.payer is _undefined:
            body.payer = AccountRef(self._operator.id)

        # 创建分账账单
        split_bill = await self.insert(
            SplitBill(
                _task_context=self,
                _id=SplitBillRef(0),
                created_by=self._operator.id,
                **body.dump_to_dict(),
            )
        )

        # 创建贡献记录
        contributions = []
        from .contribution import ContributionManager

        for contribution_editable in body.contributions:
            contributions.append(
                await ContributionManager(self).create(
                    split_bill_id=split_bill._id, body=contribution_editable
                )
            )

        submitted = False
        if submit:
            split_bill = await self.submit()
            submitted = True

        self._task_result.status = TaskStatus.CREATED
        return SplitBillV2CreateRes(
            **split_bill.dump_to_dict(), contributions=contributions, submitted=submitted
        )

    @listen_to(Method.DELETE, "/{split_bill_id}")
    def delete(self, split_bill_id: Opt[SplitBillRef] = None):
        return CommonManager.delete(self, _id=split_bill_id)

    @listen_to(Method.PUT, "/{split_bill_id}/submit")
    async def submit(self, split_bill_id: Opt[SplitBillRef] = None) -> SplitBill:
        """提交分账账单"""
        split_bill = await self._get_scheme(_id=split_bill_id)
        split_bill.submit()
        split_bill = await self._update_scheme(split_bill)
        await self._emit(".submitted", {"split_bill_id": split_bill._id})  # 也是事务的一部分啊
        return split_bill

    @listen_to(Method.PUT, "/{split_bill_id}/reject")
    async def reject(self, split_bill_id: SplitBillRef):
        """驳回分账账单"""
        split_bill = await self._get_scheme(_id=split_bill_id)

        stakeholder_type = await self.must_be_stakeholder(split_bill_id)
        if stakeholder_type == "contributor":
            from .contribution import ContributionManager

            if not ContributionManager(self).is_contributed(
                split_bill_id=split_bill_id, contributor=self._operator.id
            ):
                raise Conflict("You have contributed, you can't reject")

        split_bill.reject()

        # 退款
        await self._refund_contributed(split_bill_id=split_bill_id)

        split_bill = await self._update_scheme(split_bill)

        await self._emit(".rejected", {"split_bill_id": split_bill._id})

        return split_bill

    @listen_to(Method.PUT, "/{split_bill_id}/prepay_paid")
    async def prepay_paid(
        self, split_bill_id: SplitBillRef, amount: int, body: SplitBillForPatch
    ) -> SplitBill:
        """付前账单已实付

        :param amount: 实付金额
        :param body: 更新其它信息

            details,payee,proof
        """
        split_bill = await self._get_scheme(_id=split_bill_id)

        if self._operator.id != split_bill.payer:
            raise Forbidden("must be payer")

        await split_bill.prepay_paid(
            amount=amount, details=body.details, payee=body.payee, proof=body.proof
        )

        from .contribution import ContributionManager

        if split_bill.amount is None or split_bill.estimate_amount is None:
            raise ParamsInvalid("split bill amount (and estimate_amount) can't be None")
        contributed_amount: int = await split_bill.get_contributed_amount()
        if split_bill.amount < contributed_amount:  # 退款
            self._logger.info("Refund oversupplement to contributors")

            try:
                await ContributionManager(self).refund(split_bill_id=split_bill_id, full=False)
            except Exception:
                self._logger.error("Failed to refund oversupplement")
                split_bill.status = SplitBillStatus.ERROR
        elif split_bill.amount > contributed_amount:  # 补充
            self._logger.info("Contributors need to pay more")

            # 创建补充账单
            # 生成新的贡献记录（相对不变，绝对去除）
            new_contributions: typing.List[ContributionEditable] = []
            for contribution in await split_bill.get_contributions():
                if contribution.is_rel():
                    new_contributions.append(
                        ContributionEditable(
                            cid=ContributionKeys(
                                split_bill=SplitBillRef(0),
                                contributor=contribution.cid.contributor,
                            ),
                            relative_amount=contribution.relative_amount,
                        )
                    )
            sub_split_bill = await self.create(
                body=SplitBillForCreate(
                    _id=SplitBillRef(0),
                    type=SplitBillType.POSTPAY,
                    partner_request=split_bill.partner_request,
                    created_by=split_bill.payer,
                    title=(f"补充{split_bill.title}")[:12],  # TODO i18n
                    description="Due to the payer paid more than\
                          the total contributed amount, a new split bill is \
                              created to collect the missing amount",
                    payer=split_bill.payer,
                    payee=split_bill.payee,
                    amount=split_bill.amount - split_bill.estimate_amount,
                    paid_at=split_bill.paid_at,
                    currency=split_bill.currency,
                    proof=split_bill._id,
                    contributions=new_contributions,
                ),
                submit=True,
            )

            split_bill.sub_split_bill = sub_split_bill._id

        split_bill = await self._update_scheme(split_bill)

        await self._emit(".prepay_paid", {"split_bill_id": split_bill._id})
        if SupabaseUser.from_id(split_bill.payer).is_serv():  # TODO
            # TODO 代付者是平台本身，24h 后直接关闭
            pass

        return split_bill

    @listen_to(Method.PUT, "/{split_bill_id}/challenge_amount")
    async def challenge_amount(
        self, split_bill_id: SplitBillRef, body: Anno[str, StrConverter(min=6, max=120)]
    ) -> SplitBill:
        """贡献者异议"""
        split_bill = await self._get_scheme(split_bill_id)

        await self.must_be_contributor()
        if not split_bill.paid_at:
            raise Conflict("not paid yet")
        if (get_datetimez() - split_bill.paid_at) > datetime.timedelta(hours=24):
            raise Conflict("after paid 24h")

        self.status = SplitBillStatus.ON_PROSECUTED

        self._logger.info(
            "Contributor is challenging split bill amount",
            reason=body,  # TODO 报告异议原因给人工服务而不是写在日志中
            contributor=self._operator.id,
        )

        return await self._update_scheme(split_bill)

    def _get_transfer_callback_url(
        self,
        split_bill_id: SplitBillRef,
        transfer_on: PaymentPlatform,
    ) -> str:
        """
        转移支付类分摊操作的回调地址

        SERVER_HOST + API_ENPOINT + /split_bill/{split_bill_id}/transfered/{payment_platform}
        """
        return f"https://{get_transport_setting().http_real_host}/split_bill/{
            split_bill_id
        }/transferred/{transfer_on}"

    def _get_transfer_id(self, split_bill_id: SplitBillRef) -> str:
        return encryption.md5(f"split_bill-#{split_bill_id}-transfer")

    @listen_to(Method.POST, "/{split_bill_id}/transfer")
    async def transfer(
        self,
        payment_platform: PaymentPlatform,
        split_bill_id: Opt[SplitBillRef] = None,
    ) -> SplitBillV1InitiateTransferRes:
        """转移支付"""
        split_bill = await self._get_scheme(_id=split_bill_id)

        await split_bill.can_transfer()

        if split_bill.amount is None:
            raise ParamsInvalid("amount is None")

        transfer_id = self._get_transfer_id(
            split_bill_id=split_bill._id,
        )
        transfer_res = (
            PAYMENT_GATEWAY[payment_platform]
            .get(self)
            .transfer(
                _id=transfer_id,
                name=f"transfer of split_bill #{split_bill_id}",  # TODO i18n
                remark="Transfer split payment to payer",
                amount=split_bill.amount,
                payee=split_bill.payer,
                currency=split_bill.currency,
                callback_url=self._get_transfer_callback_url(
                    split_bill_id=split_bill._id, transfer_on=payment_platform
                ),
                scene=TransferScene.SPLIT_BILL,
                report_infos=[{"info_type": "采购商品名称", "info_content": split_bill.title}],
            )
        )

        split_bill.transfer_initiated()
        await self._update_scheme(split_bill)

        self._task_result.status = TaskStatus.CREATED
        return SplitBillV1InitiateTransferRes(package_info=transfer_res)

    @listen_to(
        Method.POST, "/{split_bill_id}/transferred/{payment_platform}/{payment_platform_id}"
    )
    async def on_transfer_callback(
        self,
        split_bill_id: SplitBillRef,
        payment_platform: PaymentPlatform,
        payment_platform_id: str,
    ) -> None:
        """处理转移支付回调"""
        pm = PAYMENT_GATEWAY[payment_platform].get_by_id(payment_platform_id, self)
        transaction = pm.resolve_transfer_callback(self._task)

        split_bill = await self._get_scheme(split_bill_id)
        if transaction.is_success():
            split_bill.transferred()
        elif transaction.is_failed():
            split_bill.transfer_failed()

        await self._update_scheme(split_bill)

    # TODO check contribution expired bills
    async def is_contribute_expired(self, split_bill_id: Opt[SplitBillRef] = None) -> bool:
        """检查是否贡献已超时"""
        split_bill = await self._get_scheme(_id=split_bill_id)

        if split_bill.contribute_before is not None:
            return get_datetimez() > split_bill.contribute_before and (
                not (await split_bill.is_contributed())
            )
        return False

    async def _on_contribution_expired(self, split_bill_id: SplitBillRef):
        """处理贡献超时"""
        await self.cancel(
            split_bill_id=split_bill_id, reason=SplitBillCancelReason.CONTRIBUTION_EXPIRED
        )

    async def _refund_contributed(self, split_bill_id: SplitBillRef, reason: Opt[str] = None):
        """退还已贡献的款项"""
        from .contribution import ContributionManager

        cm = ContributionManager(self)
        await cm.refund(
            split_bill_id=split_bill_id,
            full=True,
            reason=reason,  # TODO i18n
        )

    @listen_to(Method.PUT, "/{split_bill_id}/cancel")
    async def cancel(
        self, split_bill_id: SplitBillRef, reason: SplitBillCancelReason
    ) -> SplitBill:
        """取消分账账单

        TODO 事务性
        """
        split_bill = await self._get_scheme(_id=split_bill_id)

        split_bill.cancel(reason=reason)

        # 退款
        await self._refund_contributed(split_bill_id=split_bill_id, reason=reason.value)

        split_bill = await self._update_scheme(split_bill)

        await self._emit(".cancelled", {"split_bill_id": split_bill._id})

        return split_bill

    async def on_a_contribution_contributed(self, split_bill_id: SplitBillRef):
        """处理一个贡献记录已贡献"""
        split_bill = await self._get_scheme(split_bill_id)
        if split_bill.is_contributed():
            await self._emit(".contributed", {"split_bill_id": split_bill_id})
