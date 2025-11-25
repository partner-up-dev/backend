"""搭子请求合并请求数据模型"""

__all__ = ["PRMergeRequestStatus", "PRMergeRequestRef", "PRMergeRequest"]

import datetime
import typing
from typing import Optional as Opt
from blue_firmament.scheme import field, FieldT, field_validator
from blue_firmament.scheme.enum import Status
from blue_firmament.task.context.common import SoCommonTC
from blue_firmament.utils.datetime_ import get_datetimez
from blue_firmament.exceptions import ParamsInvalid
from account.schemas import AccountRef
from dal import SupabaseAnonPostgrest
from .partner import PartnerRoleRef
from .base import (
    PRTypedContent,
    PartnerRequestEditable,
    PartnerRequestRef,
    PartnerRequestL2Type,
    PartnerRequest,
)


class PRMergeRequestStatus(Status):
    """搭子请求合并请求状态"""

    DRAFT = "draft"
    PENDING = "pending"
    """等待审批
    """
    CLOSED = "closed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    """已过期
    
    - 来源搭子请求已经不处于可合并状态
    """

    def to_pending(self):
        return self._to_target_status(self.PENDING, self.DRAFT)

    def to_closed(self):
        return self._to_target_status(self.CLOSED, self.PENDING)

    def to_rejected(self):
        return self._to_target_status(self.REJECTED, self.PENDING)

    def to_expired(self):
        return self._to_target_status(self.EXPIRED, self.PENDING)


PRMergeRequestRef: typing.TypeAlias = int
"""搭子请求合并请求ID"""
NewPRTypedContentTV = typing.TypeVar("NewPRTypedContentTV", bound=PRTypedContent)


class PRMergeRequest(
    SoCommonTC,
    typing.Generic[NewPRTypedContentTV],
    dal=SupabaseAnonPostgrest,
    dal_path=("merge_request", "partner_request"),
):
    """搭子请求合并请求"""

    id: PRMergeRequestRef = 0
    created_at: FieldT[datetime.datetime] = field(default_factory=get_datetimez)
    created_by: FieldT[AccountRef]
    status: FieldT[PRMergeRequestStatus] = field(default=PRMergeRequestStatus.DRAFT)
    froms: FieldT[tuple[PartnerRequestRef, PartnerRequestRef]] = field(default_factory=tuple)
    """被合并的搭子请求
    
    - 限制两个
    - 第一个一定是是本合并请求创建者的
    """
    to: Opt[PartnerRequestRef] = None
    n_title: Opt[str] = None
    n_introduction: Opt[str] = None
    n_created_by: AccountRef
    n_partners: FieldT[list[tuple[PartnerRoleRef, Opt[AccountRef]]]] = field(default_factory=list)
    n_typed_content: NewPRTypedContentTV

    @field_validator(froms)
    async def _froms_joinable(self, value: set[PartnerRequestRef]):
        """被合并的搭子请求都处于可加入

        仅草稿、就绪时
        """
        if self.status in (PRMergeRequestStatus.DRAFT, PRMergeRequestStatus.PENDING):
            statuses = await self._daos(PartnerRequest).select_field(
                PartnerRequest.status, PartnerRequest._id.in_(value)
            )
            if not all(s.is_joinable() for s in statuses):
                raise ParamsInvalid("All froms must be joinable.")

    @field_validator(froms)
    async def _froms_type_same(self, value: set[PartnerRequestRef]):
        """被合并的搭子请求类型一致"""
        types = await self._daos(PartnerRequest).select_field(
            PartnerRequest.type, PartnerRequest._id.in_(value)
        )
        if not all(t == types[0] for t in types):
            raise ParamsInvalid("All froms must be the same type.")

    async def _get_pr_type(self) -> PartnerRequestL2Type:
        """获取合并后的搭子请求类型"""
        return await self._daos(PartnerRequest).select_a_field(
            PartnerRequest.type, PartnerRequest._id.in_(self.froms)
        )

    async def get_new_pr_editable(self) -> PartnerRequestEditable:
        return PartnerRequestEditable(
            _task_context=self._task_context,
            _id=PartnerRequestRef(0),
            type=(await self._get_pr_type()),
            created_by=self.n_created_by,
            title=self.n_title,
            introduction=self.n_introduction,
        )
