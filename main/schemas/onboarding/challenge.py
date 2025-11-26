"""挑战的数据模型

siyuan://blocks/20250507205821-r9xa0jb
"""

import datetime
import typing
from blue_firmament.scheme import BusinessScheme, BaseScheme, field, FieldT
from blue_firmament.utils.datetime_ import get_datetimez
from ..account import AccountRef
from .task import TaskRef


ChallengeRef = typing.NewType('ChallengeRef', int)
"""挑战 ID"""
class Challenge(BusinessScheme[ChallengeRef], key_type=ChallengeRef):

    """挑战数据模型
    
    `APIFOX <https://app.apifox.com/link/project/4406548/apis/schema-152877933>`_
    """
    __schema_name__ = "onboarding"
    __table_name__ = "challenge"

    title: str
    description: str
    wallpaper: str
    created_at: FieldT[datetime.datetime] = field(default_factory=get_datetimez)
    """创建时间
    """
    expired_at: datetime.datetime
    """截止时
    """
    resettable: bool = False
    """是否可重置
    """
    mul_reward: bool = False
    """是否允许多倍奖励
    """
    reward: str
    """奖励函数

    - 执行以发放一次奖励
    - 输入用户 ID
    """
    tasks: typing.List[TaskRef]


class RewardRecord(BaseScheme):

    """奖励发放记录数据模型
    """
    challenge: ChallengeRef
    account: AccountRef
    count: FieldT[int] = field(0)  # min = 0

