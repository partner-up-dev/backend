"""信息流列表数据模型
"""

import enum
import typing
from typing import Optional as Opt
from blue_firmament.scheme import (
    BaseScheme, BusinessScheme,
    field, FieldT
)
from blue_firmament.scheme.field import Field
from blue_firmament.task.context import SoCommonTC
from ..partner_request import PartnerRequestType
from ..account import AccountRef

if typing.TYPE_CHECKING:
    from .content import FeedContentItemRef


class FeedListType(enum.Enum):
    """信息流列表类型
    """

    FOR_YOU = 'for_you'
    """为你推荐"""
    PR_TYPE = "pr_type"
    """搭子请求类型"""

T = typing.TypeVar('T')
class FeedListParams(Field[T], typing.Generic[T]):
    """信息流列表参数
    """

PRTypeParamsT = typing.Set[PartnerRequestType]
class PRTypeParams(FeedListParams[PRTypeParamsT]):
    """搭子请求类型信息流列表的参数
    """
    def __init__(self):
        super().__init__(default_factory=set)
        self._set_converter_from_anno(PRTypeParamsT)

FeedListRef = typing.NewType('FeedListRef', int)
"""信息流列表 ID"""
class FeedList(SoCommonTC, BusinessScheme[FeedListRef], key_type=FeedListRef):
    """信息流列表
    """

    __schema_name__ = "feed"
    __table_name__ = "list"

    type: FeedListType
    created_by: AccountRef
    title: Opt[str] = None # TODO min=1, max=6
    description: Opt[str] = None  # TODO max=60
    params: FeedListParams = FeedListParams(None)
    """参数
    """
    content: FieldT[typing.Set["FeedContentItemRef"]] = field(default_factory=set)


class PRTypeFeedList(FeedList):
    """搭子请求类型信息流列表
    """

    type: FeedListType = FeedListType.PR_TYPE
    params: PRTypeParams = PRTypeParams()


class FeedListSimple(BaseScheme):

    """信息流列表简易
    """

    __proxy__ = False
    
    _id: FeedListRef
    title: Opt[str] = None

    @classmethod
    def from_base(cls, base: FeedList) -> "FeedListSimple":
        """从基础信息流列表转换
        """
        return cls(
            _id=base._id,
            title=base.title
        )

