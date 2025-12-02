"""Account Schemas - SQLModel Database Models."""

__all__ = [
    "AccountRef",
    "GeoProfile",
    "BaseProfile",
    "BaseProfileEditable",
    "AccountProfileSimple",
    "AccountConfig",
    "Gender",
    "MBTI",
]

import typing
import enum
import sqlalchemy
import sqlmodel
from typing import Optional as Opt
from pydantic import BaseModel
from utils.base import generate_random_string


AccountRef: typing.TypeAlias = str
"""帐号ID类型"""

LocationRef: typing.TypeAlias = str


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


class GeoProfile(sqlmodel.SQLModel, table=True):
    """帐号地理资料"""

    __tablename__ = "geo_profile"  # type: ignore
    __table_args__ = {"schema": "account"}

    id: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.UUID, primary_key=True),
    )
    workplace: Opt[LocationRef] = sqlmodel.Field(default=None)
    """工作地址"""
    residence: Opt[LocationRef] = sqlmodel.Field(default=None)
    """居住地址"""


NICKNAME_MAX_LENGTH = 12
NICKNAME_MIN_LENGTH = 1


class BaseProfile(sqlmodel.SQLModel, table=True):
    """账号基础资料"""

    __tablename__ = "base_profile"  # type: ignore
    __table_args__ = {"schema": "account"}

    id: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.UUID, primary_key=True),
    )
    nickname: str = sqlmodel.Field(default_factory=generate_random_string)
    avatar: Opt[str] = sqlmodel.Field(default=None)
    wallpaper: Opt[str] = sqlmodel.Field(default=None)
    bio: Opt[str] = sqlmodel.Field(default=None)
    gender: Opt[str] = sqlmodel.Field(default=None)
    """性别"""
    mbti: Opt[str] = sqlmodel.Field(default=None)
    """MBTI性格类型"""
    age_range: Opt[int] = sqlmodel.Field(default=None)
    """年龄范围
    
    0: 14 ~ 18
    1: 19 ~ 24
    2: 25 ~ 35
    3: 36 ~ 45
    4: 46 ~ 55
    5: 56 ~ 60
    """


class BaseProfileEditable(BaseModel):
    """Editable fields for BaseProfile."""

    nickname: Opt[str] = None
    avatar: Opt[str] = None
    wallpaper: Opt[str] = None
    bio: Opt[str] = None
    gender: Opt[str] = None
    mbti: Opt[str] = None
    age_range: Opt[int] = None


class AccountConfig(sqlmodel.SQLModel, table=True):
    """账号配置"""

    __tablename__ = "config"  # type: ignore
    __table_args__ = {"schema": "account"}

    id: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.UUID, primary_key=True),
    )
    public_profile_fields: Opt[str] = sqlmodel.Field(default=None)  # JSON array
    """公开的资料字段
    
    - None 则全部公开
    - id, nickname, avatar, wallpaper 一定是公开的
    """

    def filter_public(self, base_profile: BaseProfile) -> "BaseProfile":
        """过滤掉BaseProfile中非公开字段

        :return: BaseProfile
            非公开字段不会被设置
        """
        import json

        if self.public_profile_fields is None:
            return base_profile

        public_fields = (
            json.loads(self.public_profile_fields) if self.public_profile_fields else []
        )
        filtered = BaseProfile(
            id=base_profile.id,
            nickname=base_profile.nickname,
            avatar=base_profile.avatar,
            wallpaper=base_profile.wallpaper,
        )
        for field_name in public_fields:
            if hasattr(base_profile, field_name):
                setattr(filtered, field_name, getattr(base_profile, field_name))
        return filtered


class AccountProfileSimple(BaseModel):
    """账号简易展示数据模型"""

    id: AccountRef
    nickname: Opt[str] = None
    avatar: Opt[str] = None
