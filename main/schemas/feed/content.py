"""信息流内容数据模型
"""

import enum
import typing
from blue_firmament.scheme import (
    BusinessScheme
)
from blue_firmament.scheme.field import Field
from ..partner_request import PartnerRequestRef

if typing.TYPE_CHECKING:
    pass


T = typing.TypeVar('T')

class FeedContentItemType(enum.Enum):
    """信息流条目类型
    """
    
    PARTNER_REQUEST = "partner_request"
    """搭子请求"""

class FeedContentItemContent(Field[T], typing.Generic[T]):
    """信息流条目内容"""

class PRTypeContent(FeedContentItemContent[PartnerRequestRef]):
    """搭子请求类型信息流条目内容
    """
    def __init__(self):
        super().__init__()
        self._set_converter_from_anno(PartnerRequestRef)


FeedContentItemRef = typing.NewType('FeedContentItemRef', int)
class FeedContentItem(BusinessScheme[FeedContentItemRef], key_type=FeedContentItemRef):

    """信息流条目
    """

    __schema_name__ = "feed"
    __table_name__ = "content_item"

    type: FeedContentItemType
    content: FeedContentItemContent


class PRTypeFeedContentItem(FeedContentItem):
    """搭子请求类型信息流条目
    """

    type: FeedContentItemType = FeedContentItemType.PARTNER_REQUEST
    content: PRTypeContent = PRTypeContent()
