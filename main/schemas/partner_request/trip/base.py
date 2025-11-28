"""出行搭子请求数据模型"""

import enum
from typing import Optional as Opt, List
from pydantic import BaseModel
from ...base.route import RouteItem


class TripPurpose(enum.Enum):
    """出行目的"""
    AIRPORT_PICKUP = "airport_pickup"
    """接机"""
    AIRPORT_DROPOFF = "airport_dropoff"
    """送机"""
    RAILWAY_PICKUP = "railway_pickup"
    """接火车"""
    RAILWAY_DROPOFF = "railway_dropoff"
    """送火车"""
    COMMON = "common"
    """无"""
    COMMUTE = "commute"
    """通勤"""


class TripPreference(BaseModel):
    """出行偏好"""
    purpose: Opt[TripPurpose] = None
    luggage: Opt[int] = None
    """行李数量（单位：升）"""
    flight: Opt[str] = None
    """航班号"""
    railway: Opt[str] = None
    """车次号"""


class TripPRContent(BaseModel):
    """出行搭子请求特有内容"""
    id: int
    route: List[RouteItem] = []
    """路线"""
    trip_preference: Opt[TripPreference] = None
    """出行偏好"""


class TripPartnerRequest(TripPRContent):
    """出行搭子请求"""
    pass
