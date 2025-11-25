__all__ = ["AccountRef", "GeoProfile", "BaseProfile", "AccountProfileSimple", "AccountConfig"]

import typing
from typing import Annotated as Anno, Literal as Lit, Optional as Opt
from blue_firmament.scheme import BaseScheme, field, FieldT, EditableScheme
from main.schemas.base import Gender, MBTI
from main.schemas.base.route import LocationRef
from dal import SupabaseAnonPostgrest
from utils.base import generate_random_string


AccountRef: typing.TypeAlias = str
"""帐号ID类型
"""


class GeoProfile(BaseScheme, dal=SupabaseAnonPostgrest, dal_path=("geo_profile", "account")):
    """帐号地理资料"""

    id: FieldT[AccountRef] = field(is_key=True)
    workplace: FieldT[LocationRef | None] = field(None)
    """工作地址"""
    residence: FieldT[LocationRef | None] = field(None)
    """居住地址"""


NICKNAME_MAX_LENGTH = 12
NICKNAME_MIN_LENGTH = 1


class BaseProfile(BaseScheme, dal=SupabaseAnonPostgrest, dal_path=("base_profile", "account")):
    """账号基础资料"""

    id: FieldT[AccountRef] = field(
        dump_flags={
            "managed",
        },
        is_key=True,
    )
    # nickname: str = field(min_length=NICKNAME_MIN_LENGTH, max_length=NICKNAME_MAX_LENGTH) # TODO wait for support
    nickname: FieldT[str] = field(default_factory=generate_random_string)
    avatar: FieldT[Opt[None]] = field(default=None)
    wallpaper: FieldT[Opt[None]] = field(default=None)
    bio: FieldT[Opt[None]] = field(default=None)
    gender: FieldT[Opt[Gender]] = field(default=None)
    """性别"""
    mbti: FieldT[Opt[MBTI]] = field(default=None)
    """MBTI性格类型"""
    age_range: FieldT[Opt[None]] = field(default=None)  # TODO add validator for element range
    """年龄范围
    
    0: 14 ~ 18
    1: 19 ~ 24
    2: 25 ~ 35
    3: 36 ~ 45
    4: 46 ~ 55
    5: 56 ~ 60
    """


class BaseProfileEditable(
    BaseProfile,
    EditableScheme,
    default_exclude_dump_flags={
        "managed",
    },
): ...


class AccountConfig(BaseScheme, dal=SupabaseAnonPostgrest, dal_path=("config", "account")):
    id: FieldT[AccountRef] = field(is_key=True)
    public_profile_fields: FieldT[Opt[set[str]]] = field(default=None)
    """公开的资料字段
    
    - None 则全部公开
    - id, nickname, avatar, wallpaper 一定是公开的
    """

    def filter_public(self, base_profile: BaseProfile) -> BaseProfile:
        """过滤掉BaseProfile中非公开字段

        :return: BaseProfile
            非公开字段不会被设置，因此可以通过 `dump_to_dict(exclude_unset=True)`
            获得不包含非公开字段的字典
        """
        if self.public_profile_fields is None:
            return base_profile
        filtered_base_profile = BaseProfile(
            id=base_profile.id,
            nickname=base_profile.nickname,
            avatar=base_profile.avatar,
            wallpaper=base_profile.wallpaper,
        )
        for i in self.public_profile_fields:
            filtered_base_profile[i] = base_profile[i]
        return filtered_base_profile


class AccountProfileSimple(BaseScheme):
    """账号简易展示数据模型"""

    id: AccountRef
    nickname: Opt[None]
    avatar: Opt[None]
