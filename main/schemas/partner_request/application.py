"""搭子申请数据模型"""

__all__ = [
    "PartnerApplicationStatus",
    "SubPartnerApplication",
    "PartnerApplicationRef",
    "PartnerApplication",
]

import datetime
import typing
from typing import Optional as Opt

from blue_firmament.exceptions import Conflict, Duplicate, NotFound
from blue_firmament.scheme import (
    BaseScheme,
    BusinessScheme,
    FieldT,
    field,
    field_validator,
    scheme_validator,
)
from blue_firmament.scheme.enum import Status
from blue_firmament.task.context import SoCommonTC

from dal import SupabaseAnonPostgrest
from account.schemas import AccountRef
from communication.schemas.chat import ChatRef
from .base import PartnerRequest, PartnerRequestRef
from . import PartnerRoleRef, Partner


class PartnerApplicationStatus(Status):
    """搭子申请状态"""

    PENDING = "pending"
    """待审批"""
    APPROVED = "approved"
    """通过
    
    只要有一个子申请通过即算作通过
    """
    REJECTED = "rejected"
    """拒绝"""
    WITHDRAWN = "withdrawn"
    """已撤回
    
    撤回之后可以fork出一份新的申请再提交
    """
    EXPIRED = "expired"
    """已过期
    """

    def to_rejected(self):
        return self._to_target_status(PartnerApplicationStatus.REJECTED, *self.open_status())

    def to_approved(self):
        return self._to_target_status(PartnerApplicationStatus.APPROVED, *self.open_status())

    def to_withdrawn(self):
        return self._to_target_status(PartnerApplicationStatus.WITHDRAWN, *self.open_status())

    def to_expired(self):
        return self._to_target_status(PartnerApplicationStatus.EXPIRED, *self.open_status())

    def is_open(self) -> bool:
        """是否可以操作（审批、撤回、过期等）"""
        return self in self.open_status()

    def is_closed(self) -> bool:
        """是否已关闭"""
        return self in self.closed_status()

    @classmethod
    def closed_status(cls) -> typing.Tuple["PartnerApplicationStatus", ...]:
        """属于已关闭的状态"""
        return (cls.APPROVED, cls.REJECTED, cls.WITHDRAWN, cls.EXPIRED)

    @classmethod
    def open_status(cls) -> typing.Tuple["PartnerApplicationStatus", ...]:
        """属于开放的状态"""
        return (cls.PENDING,)


class SubPartnerApplication(BaseScheme, proxy=False):
    """搭子申请子申请数据模型"""

    role: FieldT[PartnerRoleRef]
    """搭子角色 ID
    """
    rationale: FieldT[Opt[str]] = field(None)  # TODO 6 - 200
    """申请理由
    """


PartnerApplicationRef = typing.NewType("PartnerApplicationRef", int)
"""搭子申请 ID"""
WITHDRAW_REASON_MIN = 6
WITHDRAW_REASON_MAX = 60


class PartnerApplication(
    BusinessScheme[PartnerApplicationRef],
    SoCommonTC,
    key_type=PartnerApplicationRef,
    dal=SupabaseAnonPostgrest,
    dal_path=("application", "partner_request"),
):
    """搭子申请数据模型"""

    created_at: FieldT[datetime.datetime] = field(default_factory=datetime.datetime.now)
    status: FieldT[PartnerApplicationStatus] = field(default=PartnerApplicationStatus.PENDING)
    partner_request: FieldT[PartnerRequestRef] = field()
    """所属搭子请求
    """
    applicant: FieldT[AccountRef] = field()
    chat: FieldT[ChatRef]
    eclose_reason: FieldT[Opt[str]] = field(default=None)  # TODO add min/max
    """撤回或驳回的理由
    """
    sub_applications: FieldT[typing.List[SubPartnerApplication]] = field(
        default_factory=list
    )  # min=1

    @field_validator(partner_request)
    async def pr_must_joinable(self, value: PartnerRequestRef):
        """搭子请求必须是可加入的

        - 如果本搭子申请已经关闭，则不需要检查
        - 如果搭子请求不可申请且本搭子申请已经创建，则过期
        - 否则抛出异常
        """
        if not self.status.is_closed():
            # FIXME 不好的实践，应该基于 PartnerRequest 的 is_joinable 方法
            pr_status = await self._daos(PartnerRequest).select_a_field(
                PartnerRequest.status,
                value,
            )
            if not pr_status.is_joinable():
                if self._inserted:
                    self._logger.warning("expired")
                    self.status = self.status.to_expired()
                    await self._dao.update(self)
                else:
                    raise Conflict("PR not joinable")

    @scheme_validator
    async def not_applying(self):
        """当前操作者没有在该搭子请求有其它正在进行的搭子申请

        仅创建之前校验
        """
        if not self._inserted:
            try:
                await self._dao.select(
                    PartnerApplication._id.not_equals(self._id),
                    PartnerApplication.applicant.equals(self.applicant),
                    PartnerApplication.partner_request.equals(self.partner_request),
                    PartnerApplication.status.in_(PartnerApplicationStatus.open_status()),
                )
            except NotFound:
                return
            else:
                raise Duplicate("You have an ongoing application on this PR")

    @field_validator(sub_applications)
    async def all_sub_applications_free(self, value: typing.List[SubPartnerApplication]):
        """申请的搭子角色需空置

        - 仅进行中
        - 未创建时所有都必须空置
        - 创建后则最少有一个空置
        """
        if self.status.is_open():
            pr_partners = await self._daos(Partner).select(
                Partner.partner_request.equals(self.partner_request),
            )

            # TODO need test
            free_state = tuple(
                any(i.is_free() if i.role == sub.role else False for i in pr_partners)
                for sub in value
            )
            if (not self._inserted and not all(free_state)) or (
                self._inserted and not any(free_state)
            ):
                raise Conflict("some roles aren't free now")

    @field_validator(sub_applications)
    async def no_duplicate_roles(self, value: typing.List[SubPartnerApplication]):
        """不可以有重复的搭子角色

        - 仅未创建
        """
        if not self._inserted:
            roles = [sub.role for sub in value]
            if len(roles) != len(set(roles)):
                raise Conflict("duplicate roles in sub applications")

    def approve(self):
        self.status = self.status.to_approved()

    def reject(self, reason: str):
        self.status = self.status.to_rejected()
        self.eclose_reason = reason

    def withdraw(self, reason: str):
        self.status = self.status.to_withdrawn()
        self.eclose_reason = reason
