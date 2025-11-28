"""通勤搭子请求数据模型"""

import datetime
from typing import Optional as Opt, List
from pydantic import BaseModel
from .base import TripPRContent
from .ride_hailing import RideHailingOrderRef
from ...base import Weekday


class CommutePRContent(TripPRContent):
    """通勤搭子请求特有内容"""

    on_at: Opt[datetime.time] = None
    """上班时间"""
    off_at: Opt[datetime.time] = None
    """下班时间"""
    workdays: List[Weekday] = [
        Weekday.MONDAY,
        Weekday.TUESDAY,
        Weekday.WEDNESDAY,
        Weekday.THURSDAY,
        Weekday.FRIDAY,
    ]
    """工作日"""
    ride_hailing_orders: List[RideHailingOrderRef] = []
    """网约车订单列表"""


class CommutePartnerRequest(CommutePRContent):
    """通勤搭子请求"""
    type: str = "commute"


class CommutePREditable(BaseModel):
    """通勤搭子请求可编辑内容"""
    on_at: Opt[datetime.time] = None
    off_at: Opt[datetime.time] = None
    workdays: Opt[List[Weekday]] = None
