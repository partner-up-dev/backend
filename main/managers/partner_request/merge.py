"""搭子请求合并请求的管理器

Business logic for partner request merge operations using SQLModel and FastAPI patterns.
"""

__all__ = [
    "PRMergeRequestManager",
    "PRMergeSubmitNotification",
    "PRMergeNeedVoteNotification",
    "PRMergeResultNotification",
]

import structlog
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from ...schemas.partner_request import PartnerRequestRef, PartnerRequest
from ...schemas.partner_request.merge import (
    PRMergeRequest,
    PRMergeRequestRef,
    PRMergeRequestStatus,
)
from communication.schemas.notification import (
    NotificationContent,
    WXMPSubMessageContent,
    WXSASubMessageContent,
)


logger = structlog.get_logger(__name__)


class PRMergeSubmitNotification(NotificationContent):
    """Notification for merge request submission."""

    def __init__(self, from_pr: PartnerRequestRef, to_merge_pr_count: int) -> None:
        self.from_pr = from_pr
        self.to_merge_pr_count = to_merge_pr_count

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
        return WXSASubMessageContent(template_id="", data={})


class PRMergeNeedVoteNotification(NotificationContent):
    """Notification for merge request vote request."""

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
        return WXSASubMessageContent(template_id="", data={})


class PRMergeResultNotification(NotificationContent):
    """Notification for merge request result."""

    def __init__(self, mr_id: PRMergeRequestRef, result: bool) -> None:
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
        return WXSASubMessageContent(template_id="", data={})


class PRMergeRequestManager:
    """Partner request merge request business logic manager.

    Provides methods for merge request operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, mr_id: PRMergeRequestRef) -> Opt[PRMergeRequest]:
        """Get a merge request by ID."""
        with SessionLocal() as db:
            return db.get(PRMergeRequest, mr_id)

    @classmethod
    def get_mine(
        cls,
        account_id: AccountRef,
        from_pr: Opt[PartnerRequestRef] = None,
        status: Opt[PRMergeRequestStatus] = None,
    ) -> list[PRMergeRequest]:
        """Get merge requests for an account.

        :param account_id: Account ID
        :param from_pr: Filter by source partner request
        :param status: Filter by status
        :return: List of merge requests
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(PRMergeRequest).where(
                PRMergeRequest.created_by == account_id
            )
            if status:
                statement = statement.where(PRMergeRequest.status == status.value)
            return list(db.exec(statement).all())

    @classmethod
    def _get_another_pr_created_by(cls, mr: PRMergeRequest) -> Opt[AccountRef]:
        """Get the created_by of the other partner request in the merge.

        :param mr: Merge request
        :return: Account ID of the other PR creator
        """
        import json

        with SessionLocal() as db:
            froms = json.loads(mr.froms) if mr.froms else []
            if len(froms) < 2:
                return None
            pr = db.get(PartnerRequest, froms[1])
            return pr.created_by if pr else None

    @classmethod
    def submit(cls, mr_id: PRMergeRequestRef) -> Opt[PRMergeRequest]:
        """Submit a merge request.

        :param mr_id: Merge request ID
        :return: Updated merge request or None
        """
        with SessionLocal() as db:
            mr = db.get(PRMergeRequest, mr_id)
            if not mr:
                return None

            mr.status = PRMergeRequestStatus.PENDING.value
            db.add(mr)
            db.commit()
            db.refresh(mr)
            return mr

    @classmethod
    def approve(
        cls,
        mr_id: PRMergeRequestRef,
        voter_id: AccountRef,
    ) -> Opt[PRMergeRequest]:
        """Approve a merge request.

        :param mr_id: Merge request ID
        :param voter_id: Voter account ID
        :return: Updated merge request or None
        :raises ValueError: If not authorized to vote
        """
        with SessionLocal() as db:
            mr = db.get(PRMergeRequest, mr_id)
            if not mr:
                return None

            another_pr_created_by = cls._get_another_pr_created_by(mr)
            if voter_id != another_pr_created_by:
                raise ValueError("Must be another PR's created_by to vote")

            mr.status = PRMergeRequestStatus.APPROVED.value
            db.add(mr)
            db.commit()
            db.refresh(mr)
            return mr

    @classmethod
    def reject(
        cls,
        mr_id: PRMergeRequestRef,
        voter_id: AccountRef,
    ) -> Opt[PRMergeRequest]:
        """Reject a merge request.

        :param mr_id: Merge request ID
        :param voter_id: Voter account ID
        :return: Updated merge request or None
        :raises ValueError: If not authorized to vote
        """
        with SessionLocal() as db:
            mr = db.get(PRMergeRequest, mr_id)
            if not mr:
                return None

            another_pr_created_by = cls._get_another_pr_created_by(mr)
            if voter_id != another_pr_created_by:
                raise ValueError("Must be another PR's created_by to vote")

            mr.status = PRMergeRequestStatus.REJECTED.value
            db.add(mr)
            db.commit()
            db.refresh(mr)
            return mr
