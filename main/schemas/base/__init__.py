""" Base schemas for main app """

import enum
import typing
from typing import Optional as Opt
from pydantic import BaseModel


class Currency(enum.Enum):
    """货币"""

    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"


class Weekday(enum.Enum):
    """星期"""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class NavigationMethod(enum.Enum):
    REDIRECT = "redirect"
    PUSH = "push"
    SWITCH_TAB = "switch_tab"
    RELAUNCH = "re_launch"


class Navigation(BaseModel):
    """Navigation model."""
    path: str
    params: dict[str, typing.Any]
    method: NavigationMethod


class Gender(enum.Enum):
    """性别枚举"""

    MALE = "male"
    FEMALE = "female"


class MBTI(enum.Enum):
    """MBTI性格枚举"""

    ISTJ = "ISTJ"
    ISFJ = "ISFJ"
    INFJ = "INFJ"
    INTJ = "INTJ"
    ISTP = "ISTP"
    ISFP = "ISFP"
    INFP = "INFP"
    INTP = "INTP"
    ESTP = "ESTP"
    ESFP = "ESFP"
    ENFP = "ENFP"
    ENTP = "ENTP"
    ESTJ = "ESTJ"
    ESFJ = "ESFJ"
    ENFJ = "ENFJ"
    ENTJ = "ENTJ"
