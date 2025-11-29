"""审批类消息管理器

Business logic for approval message operations using SQLModel and FastAPI patterns.
"""

__all__ = [
    "ApprovalMessageManager",
]

import datetime
import typing
import structlog
from typing import Optional as Opt

from core.engine import SessionLocal
from account.schemas import AccountRef
from ...schemas.chat import ChatRef
from ...schemas.message import Message, MessageRef, MessageType
from ...schemas.message.approval import (
    Approval,
    ApprovalType,
)
from main.schemas.base import Navigation


logger = structlog.get_logger(__name__)


class ApprovalMessageManager:
    """Approval message business logic manager.

    Provides methods for approval message operations without BlueFirmament dependencies.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, message_id: MessageRef) -> Opt[Message]:
        """Get an approval message by ID."""
        with SessionLocal() as db:
            message = db.get(Message, message_id)
            if message and message.type == MessageType.APPROVAL.value:
                return message
            return None

    @classmethod
    def send(
        cls,
        approvers: typing.Iterable[AccountRef],
        chat_id: ChatRef,
        created_by: AccountRef,
        approval_type: Opt[ApprovalType] = None,
        title: Opt[str] = None,
        description: Opt[str] = None,
        detail: Opt[Navigation] = None,
        closed_at: Opt[datetime.datetime] = None,
        approved_navi: Opt[Navigation] = None,
        rejected_navi: Opt[Navigation] = None,
    ) -> Message:
        """发送审批类消息

        :param approvers: 审批人列表
        :param chat_id: 聊天 ID
        :param created_by: 创建者 ID
        :param approval_type: 审批类型
        :param title: 标题
        :param description: 描述
        :param detail: 详情导航
        :param closed_at: 截止时间
        :param approved_navi: 通过后导航
        :param rejected_navi: 拒绝后导航
        :return: 创建的消息
        """
        approval = Approval(
            votes=Approval.get_votes_from_account_ids(approvers),
            closed_at=closed_at,
            title=title,
            description=description,
            detail=detail,
            approved_navigation=approved_navi,
            rejected_navigation=rejected_navi,
        )
        if approval_type is not None:
            approval.type = approval_type

        with SessionLocal() as db:
            message = Message(
                chat=chat_id,
                created_by=created_by,
                type=MessageType.APPROVAL.value,
                content=approval.model_dump_json(),
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message

    @classmethod
    def vote(
        cls,
        approval_id: MessageRef,
        approver: AccountRef,
        approve: bool,
    ) -> Approval:
        """表决

        :param approval_id: 审批消息 ID
        :param approver: 审批人 ID
        :param approve: 表决意见（同意与否）
        :return: 更新后的审批对象
        :raises ValueError: 消息不存在或不是审批消息
        """
        with SessionLocal() as db:
            message = db.get(Message, approval_id)
            if not message or message.type != MessageType.APPROVAL.value:
                raise ValueError("Approval message not found")

            approval = Approval.model_validate_json(message.content)
            approval.vote(approver=approver, approve=approve)

            # Check and execute callback
            cls._callback(approval)

            # Update message content
            message.content = approval.model_dump_json()
            db.add(message)
            db.commit()

            return approval

    @classmethod
    def _callback(cls, approval: Approval) -> None:
        """根据审批结果进行回调"""
        if approval.status.is_approved():
            logger.info("Do approved callback")
            # TODO callback with task system
        elif approval.status.is_not_approved():
            logger.info("Do rejected-like callback")
            # TODO callback with task system
