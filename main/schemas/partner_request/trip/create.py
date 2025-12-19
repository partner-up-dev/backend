"""Create request schemas for trip partner requests"""

from typing import Optional as Opt, List
from pydantic import BaseModel

from .base import TripPreference
from .ride_hailing import RideHailingPreference
from ...base.route import RouteItem
from ...base import Weekday
import datetime


class RideHailingPRCreate(BaseModel):
    """网约车搭子请求创建请求"""

    title: Opt[str] = None
    introduction: Opt[str] = None
    route: List[RouteItem] = []
    trip_preference: Opt[TripPreference] = None
    ride_hailing_preference: Opt[RideHailingPreference] = None


class CommutePRCreate(BaseModel):
    """通勤搭子请求创建请求"""

    title: Opt[str] = None
    introduction: Opt[str] = None
    route: List[RouteItem] = []
    trip_preference: Opt[TripPreference] = None
    on_at: Opt[datetime.time] = None
    off_at: Opt[datetime.time] = None
    workdays: Opt[List[Weekday]] = None
