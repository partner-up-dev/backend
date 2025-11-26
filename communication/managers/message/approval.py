"""审批类消息管理器"""

import datetime
import typing
from typing import Optional as Opt
from blue_firmament.log import get_logger
from account.schemas import AccountRef
from .main import BaseMessageManager
from ...schemas.chat import ChatRef
from ...schemas.message import MessageRef, ApprovalMessage
from ...schemas.message.approval import (
    Approval,
    ApprovalType,
)
from main.schemas.base import Navigation
from blue_firmament._types import Undefined, _undefined
from blue_firmament import listen_to, Method
from blue_firmament.log import log_manager_handler

logger = get_logger(__name__)


class ApprovalMessageManager(
    BaseMessageManager[ApprovalMessage],
    manager_name="approval",
    path_prefix=BaseMessageManager.__path_prefix__ + "/approval",
):
    async def send(
        self,
        approvers: typing.Iterable[AccountRef],
        chat_id: ChatRef,
        created_by: Opt[AccountRef] = None,
        type: Undefined | ApprovalType = _undefined,
        title: Opt[str] = None,
        description: Opt[str] = None,
        detail: Opt[Navigation] = None,
        closed_at: Opt[datetime.datetime] = None,
        approved_navi: Opt[Navigation] = None,
        rejected_navi: Opt[Navigation] = None,
    ) -> ApprovalMessage:
        approval = Approval(
            votes=Approval.get_votes_from_account_ids(approvers),
            closed_at=closed_at,
            title=title,
            description=description,
            detail=detail,
            approved_navigation=approved_navi,
            rejected_navigation=rejected_navi,
        )
        if type is not _undefined:
            approval.type = type

        res = await self.insert(
            ApprovalMessage(
                _task_context=self,
                _id=MessageRef(0),
                created_by=created_by or AccountRef(self._operator.id),
                chat=chat_id,
                content=approval,
            )
        )
        await self._sent(message_id=res._id)
        return res

    @log_manager_handler
    async def _callback(self, approval_id: MessageRef) -> None:
        """根据审批结果进行回调"""
        approval = (await self._get_scheme(_id=approval_id)).content
        if approval.status.is_approved():
            self._logger.info("Do approved callback")
            # TODO callback with task system
        elif approval.status.is_not_approved():
            self._logger.info("Do rejected-like callback")
            # TODO callback with task system

    @listen_to(Method.PUT, "/{approval_id}/{approve}")
    async def vote(self, approval_id: MessageRef, approve: bool) -> Approval:
        """表决

        :param approve: 表决意见（同意与否）
        """
        approval = (await self._get_scheme(_id=approval_id)).content

        approval.vote(approver=AccountRef(self._operator.id), approve=approve)

        if approval.status.is_open():
            # TODO notify approvers who haven't voted
            pass

        await self._callback(approval_id=approval_id)

        return (await self._update_scheme()).content
