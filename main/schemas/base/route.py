"""基础之路线数据模型"""

__all__ = [
    "LocationRef",
    "Location",
    "RouteItemDatetime",
    "RouteItem",
    "Route",
]

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
import datetime as datetime_
from blue_firmament.scheme.field import Field
from blue_firmament.scheme import BaseScheme, BusinessScheme, field, ListConverter
from dal import SupabaseAnonPostgrest


LocationRef: typing.TypeAlias = str


class Location(
    BusinessScheme[LocationRef],
    key_type=LocationRef,
    dal=SupabaseAnonPostgrest,
    dal_path=("location", "public"),
):
    friendly_address: str  # max 16
    address: typing.List[str]
    lat: float
    lng: float


class RouteItemDatetime(BaseScheme, proxy=False):
    datetime: Opt[datetime_.datetime] = None
    time: Opt[datetime_.time] = None
    bring_ahead: Opt[int] = None
    """可提前几分钟

    0: 不允许提前
    None: 不限制
    """
    put_off: Opt[int] = None
    """可推迟几分钟

    0: 不允许推迟
    None: 不限制
    """


class RouteItem(BaseScheme, proxy=False):
    datetime: RouteItemDatetime
    location: LocationRef


type RouteT = list[RouteItem]


class Route(Field[RouteT]):
    def __init__(self, **kwargs):
        kwargs["default_factory"] = list
        kwargs["converter"] = ListConverter(RouteItem, min_len=2, max_len=10)
        super().__init__(**kwargs)
