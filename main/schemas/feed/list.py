"""信息流列表数据模型 - SQLModel Database Models."""

__all__ = [
    "FeedListRef",
    "FeedListType",
    "FeedList",
    "FeedListSimple",
    "FeedListCreate",
]

import enum
import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from ..partner_request import PartnerRequestType
from ..account import AccountRef


FeedListRef: typing.TypeAlias = int
"""信息流列表 ID"""


class FeedListType(enum.Enum):
    """信息流列表类型"""

    FOR_YOU = "for_you"
    """为你推荐"""
    PR_TYPE = "pr_type"
    """搭子请求类型"""


class FeedList(sqlmodel.SQLModel, table=True):
    """信息流列表

    Database model for feed lists.
    """

    __tablename__ = "list"  # type: ignore
    __table_args__ = {"schema": "feed"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    type: str = sqlmodel.Field(default=FeedListType.FOR_YOU.value)
    """列表类型"""
    created_by: str = sqlmodel.Field()
    """创建者"""
    title: Opt[str] = sqlmodel.Field(default=None)
    """标题 (max: 6)"""
    description: Opt[str] = sqlmodel.Field(default=None)
    """描述 (max: 60)"""
    params: Opt[str] = sqlmodel.Field(default=None)
    """参数 (JSON)"""
    content: Opt[str] = sqlmodel.Field(default=None)
    """内容项IDs (JSON array)"""


class FeedListCreate(BaseModel):
    """Create model for FeedList."""
    type: FeedListType = FeedListType.FOR_YOU
    created_by: AccountRef
    title: Opt[str] = None
    description: Opt[str] = None
    params: Opt[list[PartnerRequestType]] = None


class FeedListSimple(BaseModel):
    """简易信息流列表展示模型"""
    id: FeedListRef
    title: Opt[str] = None

    @classmethod
    def from_db(cls, db_model: FeedList) -> "FeedListSimple":
        """从数据库模型转换"""
        return cls(
            id=db_model.id or 0,
            title=db_model.title
        )

