"""搭子请求合并请求的管理器"""

import asyncio
from typing import Optional as Opt
from blue_firmament import listen_to
from blue_firmament.manager import CommonManager, PresetHandlerConfig
from blue_firmament.exceptions import Forbidden, Conflict
from account.schemas import AccountRef
from ...schemas.partner_request import PartnerRequestRef, PartnerRequest
from ...schemas.partner_request.merge import (
    PRMergeRequest,
    PRMergeRequestRef,
    PRMergeRequestStatus,
)
from communication.schemas.notification import (
    NotificationContent,
    NotificationTask,
    WXMPSubMessageContent,
    WXSASubMessageContent,
)
from communication.managers.notification.channel_weixin import WXMPSubMessageManager
from communication.managers.notification.main import NotificationManager
from .partner import PartnerManager
from .base import BasePRManager, TypedPRManager


class PRMergeSubmitNotification(NotificationContent):
    def __init__(self, from_pr: PartnerRequestRef, to_merge_pr_count: int) -> None:
        self.from_pr = from_pr
        self.to_merge_pr_count = to_merge_pr_count

    # TODO i18n

    def to_wxmp_submessage(self) -> WXMPSubMessageContent:
        return WXMPSubMessageContent(
            template_id="tXaeMDJ5sUvb3eNOnjP5OzXs_7MawaGkoudMS1DtnAg",
            data={
                "thing1": {"value": "您发布的搭子请求有合适的人选，前往邀请"},
                "number2": {"value": self.to_merge_pr_count},
            },
            page=f"pages/partner_request/merge/submit?from={self.from_pr}",
        )

    def to_wxsa_submessage(self) -> WXSASubMessageContent:
        return super().to_wxsa_submessage()


class PRMergeNeedVoteNotification(NotificationContent):
    def __init__(self, mr_id: PRMergeRequestRef) -> None:
        self.mr_id = mr_id

    def to_wxmp_submessage(self) -> WXMPSubMessageContent:
        return WXMPSubMessageContent(
            template_id="qUnOcXbnjPt0AqZd348Kavq9GHXOeET11SHMEP8pLR0",
            data={
                "thing2": {"value": "搭子请求合并"},
                "thing4": {"value": "您的搭子请求与他的搭子请求匹配，对方希望与您合并"},
            },
            page=f"pages/partner_request/merge/vote?id={self.mr_id}",
        )

    def to_wxsa_submessage(self) -> WXSASubMessageContent:
        return super().to_wxsa_submessage()


class PRMergeResultNotification(NotificationContent):
    def __init__(self, mr_id: PRMergeRequestRef, result: bool) -> None:
        """
        :param result: 通过与否
        """
        self.mr_id = mr_id
        self.result = result

    def to_wxmp_submessage(self) -> WXMPSubMessageContent:
        return WXMPSubMessageContent(
            template_id="iVteTkh1BWGfsnwIwh9XLFYWH9g3EaxRdt0qrRwP3ag",
            data={
                "thing3": {"value": "搭子合并申请"},
                "phrase1": {"value": "通过" if self.result else "拒绝"},
                "thing2": {"value": "点击前往查看，我们会继续为您匹配合适的搭子"},
            },
        )

    def to_wxsa_submessage(self) -> WXSASubMessageContent:
        return super().to_wxsa_submessage()


class PRMergeRequestManager(
    CommonManager[PRMergeRequest, PRMergeRequestRef],
    path_prefix=BasePRManager.__path_prefix__ + "/merge",
    schema_cls=PRMergeRequest,
    manager_name="merge_request",
    preset_handler_config=PresetHandlerConfig(get=True),
):
    """搭子请求合并请求管理器"""

    @listen_to("GET", "/mine")
    async def get_mine(
        self, from_pr: Opt[PartnerRequestRef] = None, status: Opt[PRMergeRequestStatus] = None
    ) -> tuple[PRMergeRequest, ...]:
        """获取我的合并请求

        :param from_pr: 该搭子请求为被合并之一的
        """
        return await self._dao.select(
            PRMergeRequest.created_by.equals(self._operator.id),
            PRMergeRequest.froms.contains(from_pr) if from_pr else None,
            PRMergeRequest.status.equals(status) if status else None,
        )

    async def _get_another_pr_created_by(
        self, mr_id: Opt[PRMergeRequestRef] = None
    ) -> AccountRef:
        self._scheme = await self._get_scheme(mr_id)
        return await self._daos(PartnerRequest).select_a_field(
            PartnerRequest.created_by, PartnerRequest._id.equals(self._scheme.froms[1])
        )

    @listen_to("PUT", "/{mr_id}/submit")
    async def submit(self, mr_id: PRMergeRequestRef) -> PRMergeRequest:
        """提交合并请求"""
        self._scheme = await self._get_scheme(mr_id)

        self._scheme.status = self._scheme.status.to_pending()
        await self._update_scheme()

        # notify to another PR created_by
        antoher_pr_created_by = await self._get_another_pr_created_by(mr_id)
        await NotificationManager(self).send(
            NotificationTask(
                to=(antoher_pr_created_by,),
                channel=WXMPSubMessageManager,
                content=PRMergeNeedVoteNotification(self._scheme.id),
            )
        )

        return self._scheme

    @listen_to("PUT", "/{mr_id}/approve")
    async def approve(self, mr_id: PRMergeRequestRef) -> PRMergeRequest:
        """同意合并请求"""
        self._scheme = await self._get_scheme(mr_id)

        antoher_pr_created_by = await self._get_another_pr_created_by(mr_id)
        if self._operator.id != antoher_pr_created_by:
            raise Forbidden("must be another PR's created_by to vote")

        # check if can merge
        base_pr_manager = BasePRManager(self)
        if not all(
            # 必须得先检查，不然一个成功一个失败，当前没有 TODO 事务机制，会造成问题
            await asyncio.gather(
                *tuple(base_pr_manager.is_mergeable(from_) for from_ in self._scheme.froms)
            )
        ):
            self._scheme.status = self._scheme.status.to_expired()
            await self._update_scheme()
            raise Conflict("MR expired due to one of froms PR not mergeable")

        # start merging
        # create to_PR
        to_pr: PartnerRequest = await TypedPRManager(self)._create(
            base_editable=(await self._scheme.get_new_pr_editable()),
            content=self._scheme.n_typed_content,
        )

        # create partners
        partner_manager = PartnerManager(self)
        await asyncio.gather(
            *tuple(
                partner_manager.create(pr_id=to_pr._id, role_id=i[0], player=i[1])
                for i in self._scheme.n_partners
            )
        )

        # publish to_PR
        await base_pr_manager.publish(pr_id=to_pr._id)

        # mark froms PRs merged
        # TODO 当前用 pgsql trigger 代替了，后续使用 impersonate + bg task 完成
        # await asyncio.gather(*tuple(
        #     base_pr_manager._merged(from_)
        #     for from_ in self._scheme.froms
        # ))

        self._scheme.to = to_pr._id
        self._scheme.status = self._scheme.status.to_closed()
        await self._update_scheme()

        # TODO notify created_by
        await NotificationManager(self).send(
            NotificationTask(
                to=(self._scheme.created_by,),
                channel=WXMPSubMessageManager,
                content=PRMergeResultNotification(mr_id=self._scheme.id, result=True),
            )
        )

        return self._scheme

    @listen_to("PUT", "/{mr_id}/reject")
    async def reject(self, mr_id: PRMergeRequestRef) -> PRMergeRequest:
        """否决合并请求"""
        self._scheme = await self._get_scheme(mr_id)

        antoher_pr_created_by = await self._get_another_pr_created_by(mr_id)
        if self._operator.id != antoher_pr_created_by:
            raise Forbidden("must be another PR's created_by to vote")

        # update status
        self._scheme.status = self._scheme.status.to_closed()
        await self._update_scheme()

        # TODO notify created_by
        await NotificationManager(self).send(
            NotificationTask(
                to=(self._scheme.created_by,),
                channel=WXMPSubMessageManager,
                content=PRMergeResultNotification(mr_id=self._scheme.id, result=False),
            )
        )

        return self._scheme
