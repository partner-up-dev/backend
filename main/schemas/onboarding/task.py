"""任务数据模型
"""

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from blue_firmament.scheme import BusinessScheme, field, FieldT
from ..base import Navigation


TaskRef = typing.NewType('TaskRef', int)
"""任务 ID"""
class Task(BusinessScheme[TaskRef], key_type=TaskRef):

    """任务数据模型

    `APIFOX <https://app.apifox.com/link/project/4406548/apis/schema-165827276>`_
    """
    __schema_name__ = "onboarding"
    __table_name__ = "task"

    title: str
    description: str
    navigation: Navigation
    """辅助完成该任务的前端元素位置
    """
    progress_getter: str
    """进度获取器
    
    - 一个序列化的可调用对象。
    - 输入是用户 ID、挑战 ID，返回一个百分比值
    """