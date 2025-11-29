"""信息流内容数据模型 - SQLModel Database Models."""

__all__ = [
    "FeedContentItemRef",
    "FeedContentItemType",
    "FeedContentItem",
]

import enum
import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from ..partner_request import PartnerRequestRef


FeedContentItemRef: typing.TypeAlias = int
"""信息流条目 ID"""


class FeedContentItemType(enum.Enum):
    """信息流条目类型"""

    PARTNER_REQUEST = "partner_request"
    """搭子请求"""


class FeedContentItem(sqlmodel.SQLModel, table=True):
    """信息流条目

    Database model for feed content items.
    """

    __tablename__ = "content_item"  # type: ignore
    __table_args__ = {"schema": "feed"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    type: str = sqlmodel.Field(default=FeedContentItemType.PARTNER_REQUEST.value)
    """条目类型"""
    content: Opt[str] = sqlmodel.Field(default=None)
    """条目内容 (JSON)"""


class FeedContentItemCreate(BaseModel):
    """Create model for FeedContentItem."""
    type: FeedContentItemType = FeedContentItemType.PARTNER_REQUEST
    content: Opt[PartnerRequestRef] = None


class FeedContentItemSimple(BaseModel):
    """Simple representation of FeedContentItem."""
    id: FeedContentItemRef
    type: FeedContentItemType
    content: Opt[PartnerRequestRef] = None
