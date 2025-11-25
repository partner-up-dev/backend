"""聊天模块核心数据模型"""

import datetime
import enum
import typing
from typing import Optional as Opt

from blue_firmament.exceptions import ParamsInvalid, Conflict, NotFound
from blue_firmament.scheme import (
    BusinessScheme,
    FieldT,
    field,
    field_validator,
)
from blue_firmament.scheme.enum import Status
from blue_firmament.task.context import SoCommonTC
from blue_firmament.utils.datetime_ import get_datetimez

from dal import SupabaseAnonPostgrest

from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    from main.schemas.partner_request import PartnerRequestRef


class ChatStatus(Status):
    """聊天状态"""

    OPEN = "open"
    BLOCKED = "blocked"
    CLOSED = "closed"

    def to_closed(self):
        return self._to_target_status(self.CLOSED, self.OPEN)


class ChatType(enum.Enum):
    """聊天类型"""

    DIRECT_MESSAGE = "direct_message"
    """私信"""
    PARTNER_REQUEST = "partner_request"
    """搭子请求群聊"""
    PARTNER_APPLICATION = "partner_application"
    """搭子申请群聊"""


ChatRef: typing.TypeAlias = int
"""聊天 ID"""


class Chat(
    BusinessScheme[ChatRef],
    SoCommonTC,
    key_type=ChatRef,
    dal_path=("base", "chat"),
    dal=SupabaseAnonPostgrest,
):
    """聊天数据模型"""

    type: FieldT[ChatType]
    status: FieldT[ChatStatus] = field(default=ChatStatus.OPEN)
    created_at: FieldT[datetime.datetime] = field(default_factory=get_datetimez)
    created_by: FieldT[AccountRef]
    """创建者，即管理员
    """
    title: Opt[str] = None
    avatar: Opt[str] = None
    parent: FieldT[Opt[ChatRef]] = None
    """父聊天
    """
    members: FieldT[Opt[typing.Set[AccountRef]]] = field(default_factory=set)
    """成员列表

    类型为搭子请求、搭子申请群聊时为 None
    """

    @field_validator(members)
    def members_none_when_pr(self, value):
        """成员列表在搭子请求类型群聊时为空"""
        if self.type in (ChatType.PARTNER_APPLICATION, ChatType.PARTNER_REQUEST):
            if value is not None:
                raise ParamsInvalid("members must be None")

    async def get_pr_id(self) -> "PartnerRequestRef":
        """获取所属搭子请求的 ID

        仅在搭子请求、搭子申请群聊时有效
        """
        from interface_main.schemas.partner_request.base import PartnerRequest

        if self.type in (ChatType.PARTNER_REQUEST, ChatType.PARTNER_APPLICATION):
            return await self._daos(PartnerRequest).select_a_field(
                PartnerRequest._id,
                PartnerRequest.chat.equals(
                    self._id if self.type == ChatType.PARTNER_REQUEST else self.parent
                ),
            )
        raise NotFound("This chat don't has a PR", chat=self._id)

    async def get_members(self) -> typing.Set[AccountRef]:
        """获取聊天成员列表

        - 类型为搭子请求群聊时，为搭子请求的搭子列表
        - 类型为搭子申请群聊时，为搭子请求的搭子列表 + 创建者
        """
        if self.type in (ChatType.PARTNER_REQUEST, ChatType.PARTNER_APPLICATION):
            from app.managers.partner_request import BasePRManager

            partners = await BasePRManager(self._task_context).get_partners_account_ids(
                pr_id=(await self.get_pr_id()), exclude_history=False
            )
            partners.add(self.created_by)
            return partners
        else:
            if self.members is None:
                raise ParamsInvalid("members is None", chat=self._id)
            return self.members
