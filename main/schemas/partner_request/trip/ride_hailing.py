"""网约车搭子请求 核心数据模型"""

import typing
from typing import Optional as Opt, List
from pydantic import BaseModel
from .base import TripPRContent


RideHailingOrderRef = typing.NewType("RideHailingOrderRef", int)
RideTypeRef = typing.NewType("RideTypeRef", str)


class RideHailingPreference(BaseModel):
    """网约车偏好"""
    ride_types: List[RideTypeRef] = []
    """车型偏好"""


class RideHailingPRContent(TripPRContent):
    """网约车搭子请求特有内容"""
    ride_hailing_preference: Opt[RideHailingPreference] = None
    ride_hailing_order: Opt[RideHailingOrderRef] = None


class RideHailingPartnerRequest(RideHailingPRContent):
    """网约车搭子请求"""
    type: str = "ride_hailing"


class RideHailingPREditable(BaseModel):
    """网约车搭子请求可编辑内容"""
    ride_hailing_preference: Opt[RideHailingPreference] = None
