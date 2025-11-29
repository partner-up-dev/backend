"""挑战的数据模型 - SQLModel Database Models.

siyuan://blocks/20250507205821-r9xa0jb
"""

__all__ = [
    "ChallengeRef",
    "Challenge",
    "ChallengeCreate",
    "RewardRecord",
    "RewardRecordCreate",
]

import datetime
import typing
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel

from utils.base import get_utc_now
from ..account import AccountRef
from .task import TaskRef


ChallengeRef: typing.TypeAlias = int
"""挑战 ID"""


class Challenge(sqlmodel.SQLModel, table=True):
    """挑战数据模型

    Database model for onboarding challenges.

    `APIFOX <https://app.apifox.com/link/project/4406548/apis/schema-152877933>`_
    """
    __tablename__ = "challenge"  # type: ignore
    __table_args__ = {"schema": "onboarding"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    title: str = sqlmodel.Field()
    description: str = sqlmodel.Field()
    wallpaper: str = sqlmodel.Field()
    created_at: datetime.datetime = sqlmodel.Field(default_factory=get_utc_now)
    """创建时间"""
    expired_at: datetime.datetime = sqlmodel.Field()
    """截止时间"""
    resettable: bool = sqlmodel.Field(default=False)
    """是否可重置"""
    mul_reward: bool = sqlmodel.Field(default=False)
    """是否允许多倍奖励"""
    reward: str = sqlmodel.Field()
    """奖励函数

    - 执行以发放一次奖励
    - 输入用户 ID
    """
    tasks: Opt[str] = sqlmodel.Field(default=None)
    """任务ID列表 (JSON array)"""


class ChallengeCreate(BaseModel):
    """Create model for Challenge."""
    title: str
    description: str
    wallpaper: str
    expired_at: datetime.datetime
    resettable: bool = False
    mul_reward: bool = False
    reward: str
    tasks: list[TaskRef]


class RewardRecord(sqlmodel.SQLModel, table=True):
    """奖励发放记录数据模型

    Database model for reward records.
    """
    __tablename__ = "reward_record"  # type: ignore
    __table_args__ = {"schema": "onboarding"}

    id: Opt[int] = sqlmodel.Field(default=None, primary_key=True)
    challenge: int = sqlmodel.Field(foreign_key="onboarding.challenge.id")
    account: str = sqlmodel.Field()
    count: int = sqlmodel.Field(default=0)


class RewardRecordCreate(BaseModel):
    """Create model for RewardRecord."""
    challenge: ChallengeRef
    account: AccountRef
    count: int = 0

