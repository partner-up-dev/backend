""" """

import enum
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from blue_firmament.scheme import BaseScheme, field, FieldT
from blue_firmament.scheme.field import Field
from blue_firmament.scheme.converter import (
    FloatConverter,
    IntConverter,
    OptionalConveter,
)


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


class Navigation(BaseScheme, proxy=False):
    path: str
    params: dict[str, typing.Any]
    method: NavigationMethod


class OptAbsAmount(Field[Opt[int]]):
    """可选金额"""

    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(tp_converter=IntConverter(ge=1))
        super().__init__(**kwargs)


class OptRelAmount(Field[Opt[float]]):
    """可选的相对金额"""

    def __init__(self, **kwargs):
        kwargs["default"] = None
        kwargs["converter"] = OptionalConveter(tp_converter=FloatConverter(gt=0, le=1))
        super().__init__(**kwargs)


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
