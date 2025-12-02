"""通勤搭子请求数据模型"""

import datetime
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlmodel
from typing import Optional as Opt, List
from pydantic import BaseModel

from .base import TripPreference
from ..base import PartnerRequestRef
from ...base.route import RouteItem
from .ride_hailing import RideHailingOrderRef
from ...base import Weekday


class CommutePRContent(sqlmodel.SQLModel, table=True):
    """通勤搭子请求特有内容"""

    __tablename__ = "commute"  # type: ignore
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
    on_at: Opt[datetime.time] = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.TIMESTAMP(timezone=True)),
        default=None,
    )
    """上班时间"""
    off_at: Opt[datetime.time] = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.TIMESTAMP(timezone=True)),
        default=None,
    )
    """下班时间"""
    workdays: List[Weekday] = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.dialects.postgresql.JSONB),
        default_factory=lambda: [
            Weekday.MONDAY,
            Weekday.TUESDAY,
            Weekday.WEDNESDAY,
            Weekday.THURSDAY,
            Weekday.FRIDAY,
        ],
    )
    """工作日"""
    ride_hailing_orders: List[RideHailingOrderRef] = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.ARRAY(sqlalchemy.Integer)),
        default_factory=list,
    )
    """网约车订单列表"""


class CommutePREditable(BaseModel):
    """通勤搭子请求可编辑内容"""

    on_at: Opt[datetime.time] = None
    off_at: Opt[datetime.time] = None
    workdays: Opt[List[Weekday]] = None
