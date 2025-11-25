"""搭子请求基础数据模型"""

# __module_name__ = "PartnerRequestCommonSchema"

# schemas
import datetime
import enum
import typing
from typing import Optional as Opt, Literal as Lit

from blue_firmament.dal.query_components.operators import OrOperator
from blue_firmament.scheme import (
    BusinessScheme,
    field,
    FieldT,
    scheme_validator,
    StrConverter,
    OptionalConveter,
    EditableScheme,
)
from blue_firmament.scheme.enum import Status
from blue_firmament.scheme.field import Field
from blue_firmament.utils.datetime_ import get_datetimez
from blue_firmament.task.context import SoCommonTC
from dal import SupabaseAnonPostgrest

from .partner import Partner
from ..contract import ContractRef
from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    from communication.schemas.chat import ChatRef


# t = i18n.get_translator(__module_name__)
# def _(message: str) -> str:
#     return message


class PartnerRequestType(enum.Enum):
    TRIP = "trip"
    """出行搭子"""
    RIDE_HAILING = "ride_hailing"
    """网约车搭子"""
    COMMUTE = "commute"
    """通勤搭子"""
    HITCHHIKING = "hitchhiking"
    """便车搭子"""
    MOPED = "moped"
    """电瓶搭子"""
    TRAVEL = "travel"
    """旅游搭子"""


class PartnerRequestL2Type(enum.Enum):
    """搭子请求二级类型"""

    # 出行搭子
    RIDE_HAILING = "ride_hailing"
    """网约车搭子"""
    COMMUTE = "commute"
    """通勤搭子"""
    HITCHHIKING = "hitchhiking"
    """便车搭子"""
    MOPED = "moped"
    """电瓶搭子"""

    # 旅游搭子
    TRAVEL = "travel"
    """旅游搭子"""


class PartnerRequestStatus(Status):
    """搭子请求状态

    Docs
    ----
    - `SIYUAN <siyuan://blocks/20250429142821-ilmfo3s>`_
    """

    DRAFT = "draft"
    JOINABLE = "joinable"
    """可加入"""
    READY = "ready"
    """可执行"""
    PERFORMING = "performing"
    """执行中"""
    SETTLING = "settling"
    """结算中"""
    CLOSED = "closed"
    """正常关闭"""
    CANCELLED = "cancelled"
    """取消"""
    MERGED = "merged"
    """已合并"""

    def next(self) -> "PartnerRequestStatus":
        """下一个状态

        正常流转模式

        :raises ValueError: 如果没有下一个状态
        """
        if self == PartnerRequestStatus.DRAFT:
            return PartnerRequestStatus.JOINABLE
        elif self == PartnerRequestStatus.JOINABLE:
            return PartnerRequestStatus.READY
        elif self == PartnerRequestStatus.READY:
            return PartnerRequestStatus.PERFORMING
        elif self == PartnerRequestStatus.PERFORMING:
            return PartnerRequestStatus.SETTLING
        elif self == PartnerRequestStatus.SETTLING:
            return PartnerRequestStatus.CLOSED

        raise ValueError("No next status for %s" % self)

    def to_joinable(self) -> "Lit[PartnerRequestStatus.JOINABLE]":
        """切换到可加入"""
        return self._to_target_status(PartnerRequestStatus.JOINABLE, PartnerRequestStatus.DRAFT)

    def to_cancelled(self) -> "Lit[PartnerRequestStatus.CANCELLED]":
        """切换到取消

        可取消状态：siyuan://blocks/20250501180657-h1m6k55
        """
        return self._to_target_status(
            self.CANCELLED,
            self.JOINABLE,
            self.READY,
        )

    def to_ready(self):
        return self._to_target_status(self.READY, self.JOINABLE, self.SETTLING)

    def to_merged(self):
        return self._to_target_status(self.MERGED, self.JOINABLE)

    def is_draft(self) -> bool:
        return self == PartnerRequestStatus.DRAFT

    def is_joinable(self) -> bool:
        """是否可以加入"""
        return self in (PartnerRequestStatus.JOINABLE,)

    @classmethod
    def ongoing_status(cls) -> tuple["PartnerRequestStatus", ...]:
        """进行中的状态"""
        return (
            cls.JOINABLE,
            cls.READY,
            cls.PERFORMING,
            cls.SETTLING,
        )

    @classmethod
    def closed_status(cls) -> tuple["PartnerRequestStatus", ...]:
        """已关闭的状态"""
        return (
            cls.CLOSED,
            cls.CANCELLED,
        )


class PartnerRequestListType(enum.Enum):
    """搭子请求列表类型"""

    FAVORITE = "favorite"
    """收藏的搭子请求"""
    ONGOING = "ongoing"
    """进行中的搭子请求"""
    HISTORY = "history"
    """历史搭子请求"""
    DRAFT = "draft"
    """草稿搭子请求"""


type PRTitleT = Opt[str]


class PRTitle(Field[PRTitleT]):
    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(tp_converter=StrConverter(min=3, max=12))
        super().__init__(**kwargs)


type PRIntroductionT = Opt[str]


class PRIntroudction(Field[PRIntroductionT]):
    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(tp_converter=StrConverter(min=6, max=60))
        super().__init__(**kwargs)


PartnerRequestRef: typing.TypeAlias = int


class PartnerRequest(
    BusinessScheme[PartnerRequestRef],
    SoCommonTC,
    key_type=PartnerRequestRef,
    dump_flags={
        "_id": {
            "managed",
        }
    },
    dal=SupabaseAnonPostgrest,
    dal_path=("base", "partner_request"),
):
    type: FieldT[PartnerRequestL2Type] = field(
        dump_flags={
            "managed",
        }
    )
    """搭子请求类型
    """
    status: FieldT[PartnerRequestStatus] = field(
        default=PartnerRequestStatus.DRAFT,
        dump_flags={
            "managed",
        },
    )
    """搭子请求状态
    """
    created_at: FieldT[datetime.datetime] = field(
        default_factory=get_datetimez,
        dump_flags={
            "managed",
        },
    )
    created_by: FieldT[AccountRef] = field(
        dump_flags={
            "managed",
        }
    )
    chat: FieldT[Opt["ChatRef"]] = field(
        default=None,
        dump_flags={
            "managed",
        },
    )
    contract: FieldT[Opt[ContractRef]] = field(
        default=None,
        dump_flags={
            "managed",
        },
    )
    title: PRTitle = PRTitle()
    introduction: PRIntroudction = PRIntroudction()

    @scheme_validator
    def chat_not_nullable(self, **_) -> None:
        """聊天 ID 在草稿之外不能为空"""
        if self.status != PartnerRequestStatus.DRAFT:
            if not self.chat:
                raise ValueError("chat is not nullable after draft")

    async def is_partner(
        self,
        account_id: AccountRef,
        include_history: bool = False,
        include_created_by: bool = False,
    ) -> bool:
        """是否为该搭子请求的搭子

        :param account_id: 用户 ID
        :param include_history: 是否包含历史搭子
        :param include_created_by: 创建者算不算
        """
        if include_created_by and self.created_by == account_id:
            return True

        res = await self._daos(Partner).select(
            Partner.partner_request.equals(self._id),
            (
                Partner.player.equals(account_id)
                if not include_history
                else OrOperator(
                    Partner.player.equals(account_id), Partner.history.contains([account_id])
                )
            ),
        )
        return len(res) > 0

    @staticmethod
    def _is_partner(
        partners: list["Partner"],
        account_id: AccountRef,
        include_history: bool = False,
    ) -> bool:
        """是否在搭子列表中"""
        res = any(partner.player == account_id for partner in partners)
        # 没有依赖 partner_account_ids，这样可以避免全量遍历

        if not res:
            if include_history:
                res = any(account_id in partner.history for partner in partners)
        return res

    def is_admin(self, account_id: AccountRef) -> bool:
        """是否为管理员

        创建者是管理员
        """
        return self.created_by == account_id

    def is_bill_submittable(self) -> bool:
        """是否可以提交账单"""
        return self.status in (
            PartnerRequestStatus.READY,
            PartnerRequestStatus.PERFORMING,
            PartnerRequestStatus.SETTLING,
        )

    def is_deletable(self) -> bool:
        """是否可以删除

        草稿状态可以删除
        """
        return self.status == PartnerRequestStatus.DRAFT

    def is_mergeable(self) -> bool:
        """是否可以被合并"""
        return self.status == PartnerRequestStatus.JOINABLE


class PRTypedContent(SoCommonTC, proxy=True):
    """搭子请求类型特有内容"""

    _id: FieldT[PartnerRequestRef] = field(is_key=True)


class PartnerRequestEditable(
    EditableScheme,
    PartnerRequest,
    default_exclude_dump_flags={
        "managed",
    },
): ...
