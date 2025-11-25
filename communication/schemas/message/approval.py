"""审批类消息的数据模型"""

import typing
from typing import Optional as Opt, Annotated as Anno
import enum
import datetime
from blue_firmament.scheme import BaseScheme, field, FieldT, scheme_validator
from blue_firmament.scheme.enum import Status
from blue_firmament.utils.datetime_ import get_datetimez
from blue_firmament.exceptions import Conflict, ParamsInvalid
from account.schemas import AccountRef
from main.schemas.base import Navigation


class ApprovalStatus(Status):
    """审批状态"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

    @classmethod
    def open_status(cls):
        return (cls.PENDING,)

    def is_open(self):
        return self in self.open_status()

    def is_not_approved(self):
        """审批不通过"""
        return self in (
            ApprovalStatus.WITHDRAWN,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.REJECTED,
        )

    def is_approved(self):
        """审批通过"""
        return self == ApprovalStatus.APPROVED

    def to_approved(self):
        """转换为已通过状态"""
        return self._to_target_status(ApprovalStatus.APPROVED, *self.open_status())

    def to_rejected(self):
        """转换为已拒绝状态"""
        return self._to_target_status(ApprovalStatus.REJECTED, *self.open_status())

    def to_withdrawn(self):
        """转换为已撤回状态"""
        return self._to_target_status(ApprovalStatus.WITHDRAWN, *self.open_status())

    def to_expired(self):
        """转换为已过期状态"""
        return self._to_target_status(ApprovalStatus.EXPIRED, *self.open_status())


class ApprovalType(enum.Enum):
    """审批类型"""

    ONE_VETO = "one_veto"
    """一票否决
    """
    HALF = "half"
    """半数通过
    
    - 达到半数即通过
    - 奇数人数时，向上取整
    """


VotesT = typing.Dict[AccountRef, bool | None]
"""表决记录类型"""


class Approval(BaseScheme):
    """审批

    存储在 message.content 中
    """

    title: Opt[str] = None
    description: Opt[str] = None
    detail: Opt[Navigation] = None
    """详细信息的前端位置
    """
    closed_at: Opt[datetime.datetime] = None
    """截止时间
    """
    type: ApprovalType = ApprovalType.ONE_VETO
    status: ApprovalStatus = ApprovalStatus.PENDING
    votes: FieldT[VotesT]
    """表决记录
    
    存储有哪些人可以审批，以及他们的审批意见。
    boolean 表示是否通过，None 表示未审批
    """
    approved_navigation: Opt[Navigation] = None
    """表决同意时导航至的前端资源"""
    rejected_navigation: Opt[Navigation] = None
    """表决否决时导航至的前端资源"""

    @scheme_validator
    def check_expired(self) -> None:
        """检查是否过期

        如果过期，则修改状态为已过期
        """
        if self.status.is_open():
            if self.closed_at and self.closed_at < get_datetimez():
                self.status = ApprovalStatus.EXPIRED

    def vote(
        self,
        approver: AccountRef,
        approve: bool,
    ) -> None:
        """表决

        :param approver: 审批人 ID
        :param approve: 审批意见

            True 表示同意，False 表示否决

        条件
        ------
        - 是审批者
        - 未审批过
        - 状态开放
        """
        if self.status.is_open():
            if approver not in self.votes:
                raise ParamsInvalid("not an approver of this approval", approver=approver)
            if self.votes[approver] is None:
                self.votes[approver] = approve
                self._check_votes()
            else:
                raise Conflict("already approved", approver=approver)
        else:
            raise ParamsInvalid("approval is not open")

    def _check_votes(self) -> None:
        """检查审批记录，判断是通过、否决还是继续"""
        if self.type == ApprovalType.ONE_VETO:
            if any(v is False for v in self.votes.values()):
                self.status = ApprovalStatus.REJECTED
            elif all(v is True for v in self.votes.values()):
                self.status = ApprovalStatus.APPROVED
        elif self.type == ApprovalType.HALF:
            if len(tuple(v for v in self.votes.values() if v is True)) >= len(self.votes) / 2:
                self.status = ApprovalStatus.APPROVED
            elif len(tuple(v for v in self.votes.values() if v is False)) >= len(self.votes) / 2:
                self.status = ApprovalStatus.REJECTED
        else:
            raise ParamsInvalid("invalid approval type")

    @classmethod
    def get_votes_from_account_ids(cls, account_ids: typing.Iterable[AccountRef]) -> VotesT:
        return {account_id: None for account_id in account_ids}
