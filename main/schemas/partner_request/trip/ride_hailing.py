"""网约车搭子请求 核心数据模型"""

import typing
from typing import Optional as Opt, List
from pydantic import BaseModel
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlmodel
from .base import TripPreference
from ..base import PartnerRequestRef
from ...base.route import RouteItem


RideHailingOrderRef = typing.NewType("RideHailingOrderRef", int)
RideTypeRef = typing.NewType("RideTypeRef", str)


class RideHailingPreference(BaseModel):
    """网约车偏好"""

    ride_types: List[RideTypeRef] = []
    """车型偏好"""


class RideHailingPRContent(sqlmodel.SQLModel, table=True):
    """网约车搭子请求特有内容"""

    __tablename__ = "ride_hailing"  # type: ignore
    __table_args__ = {"schema": "partner_request"}

    id: PartnerRequestRef = sqlmodel.Field(
        sa_column=sqlmodel.Column(
            sqlalchemy.Integer,
            sqlalchemy.ForeignKey(
                "partner_request.base.id", ondelete="CASCADE", onupdate="CASCADE"
            ),
            primary_key=True,
        )
    )
    route: List[RouteItem] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlalchemy.dialects.postgresql.JSONB),
        default_factory=list,
    )
    """路线"""
    trip_preference: Opt[TripPreference] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlalchemy.dialects.postgresql.JSONB),
        default=None,
    )
    """出行偏好"""
    ride_hailing_preference: RideHailingPreference = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.dialects.postgresql.JSONB),
        default_factory=RideHailingPreference,
    )
    ride_hailing_order: Opt[RideHailingOrderRef] = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer),
        default=None,
    )


class RideHailingPREditable(BaseModel):
    """网约车搭子请求可编辑内容"""

    ride_hailing_preference: Opt[RideHailingPreference] = None
