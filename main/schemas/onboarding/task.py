"""任务数据模型 - SQLModel Database Models."""

__all__ = [
    "TaskRef",
    "Task",
    "TaskCreate",
]

import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from ..base import Navigation


TaskRef: typing.TypeAlias = int
"""任务 ID"""


class Task(sqlmodel.SQLModel, table=True):
    """任务数据模型

    Database model for onboarding tasks.

    `APIFOX <https://app.apifox.com/link/project/4406548/apis/schema-165827276>`_
    """
    __tablename__ = "task"  # type: ignore
    __table_args__ = {"schema": "onboarding"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    title: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    navigation: Opt[str] = sqlmodel.Field(default=None)
    """辅助完成该任务的前端元素位置 (JSON)"""
    progress_getter: str = sqlmodel.Field()
    """进度获取器

    - 一个序列化的可调用对象。
    - 输入是用户 ID、挑战 ID，返回一个百分比值
    """


class TaskCreate(BaseModel):
    """Create model for Task."""
    title: str
    description: str
    navigation: Opt[Navigation] = None
    progress_getter: str