__all__ = ["PRTypedUnion", "PRTypedMapper"]

import typing

from .base import PartnerRequestL2Type

from .travel import TravelPartnerRequest
from .trip.commute import CommutePartnerRequest
from .trip.ride_hailing import RideHailingPartnerRequest
from .trip.base import TripPartnerRequest

type PRTypedUnion = (
    TripPartnerRequest | RideHailingPartnerRequest | CommutePartnerRequest | TravelPartnerRequest
)
"""（二级）搭子请求数据模型集合"""


PRTypedMapper: typing.Dict[PartnerRequestL2Type, typing.Type[PRTypedUnion]] = {
    PartnerRequestL2Type.RIDE_HAILING: RideHailingPartnerRequest,
    PartnerRequestL2Type.COMMUTE: CommutePartnerRequest,
    PartnerRequestL2Type.TRAVEL: TravelPartnerRequest,
}
"""搭子请求类型到数据模型映射表"""
