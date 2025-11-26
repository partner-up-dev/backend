"""基础之路线数据模型"""

__all__ = [
    "LocationRef",
    "Location",
    "RouteItemDatetime",
    "RouteItem",
]

import typing
from typing import Optional as Opt
import datetime as datetime_
import sqlmodel
import sqlalchemy
from pydantic import BaseModel


LocationRef: typing.TypeAlias = str


class Location(sqlmodel.SQLModel, table=True):
    """Location database model."""
    __tablename__ = "location"  # type: ignore
    __table_args__ = {"schema": "public"}

    id: LocationRef = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.String, primary_key=True),
    )
    friendly_address: str = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.String(64), nullable=False)
    )  # max 16
    address: str = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    )  # JSON list[str]
    lat: float = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    )
    lng: float = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Float, nullable=False)
    )


class RouteItemDatetime(BaseModel):
    """Route item datetime model."""
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


class RouteItem(BaseModel):
    """Route item model."""
    datetime: RouteItemDatetime
    location: LocationRef
