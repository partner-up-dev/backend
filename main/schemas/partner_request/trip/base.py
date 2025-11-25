"""出行搭子请求数据模型
"""

import enum
import typing
from typing import Optional as Opt
from blue_firmament.scheme import BaseScheme, field, FieldT
from .. import PartnerRequest, PRTypedContent
from ...base.route import Route, RouteT


class TripPurpose(enum.Enum):

    """出行目的

    Docs
    ----
    - `APIFOX <https://app.apifox.com/link/project/4406548/apis/schema-146309196?branchId=5433542>`_
    """
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

class TripPreference(BaseScheme, proxy=False):
    """出行偏好

    存储在搭子请求的 trip_preference 字段中
    """
    purpose: Opt[TripPurpose] = None
    luggage: Opt[int] = None
    """行李数量

    单位：升
    """
    flight: Opt[str] = None
    """航班号"""
    railway: Opt[str] = None
    """车次号"""


class TripPRContent(PRTypedContent):
    """出行搭子请求特有内容
    """
    route: FieldT[RouteT] = Route()
    """路线"""
    trip_preference: FieldT[TripPreference] = field(default_factory=TripPreference)
    """出行偏好"""


class TripPartnerRequest(PartnerRequest, TripPRContent):
    """出行搭子请求
    """
