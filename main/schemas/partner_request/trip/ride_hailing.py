"""网约车搭子请求 核心数据模型"""

import typing
from typing import Optional as Opt
from blue_firmament.scheme import BaseScheme, field, FieldT, EditableScheme
from ..trip.base import TripPRContent, TripPartnerRequest
from .. import PartnerRequestL2Type, PartnerRequestEditable
from dal import SupabaseAnonPostgrest


RideHailingOrderRef = typing.NewType("RideHailingOrderRef", int)
RideTypeRef = typing.NewType("RideTypeRef", str)


class RideHailingPreference(BaseScheme, proxy=False):
    """网约车偏好"""

    ride_types: FieldT[typing.List[RideTypeRef]] = field(default_factory=list)
    """车型偏好
    """


class RideHailingPRContent(
    TripPRContent, dal=SupabaseAnonPostgrest, dal_path=("ride_hailing", "partner_request")
):
    """网约车搭子请求特有内容"""

    ride_hailing_preference: FieldT[Opt[RideHailingPreference]] = field(
        default_factory=RideHailingPreference
    )
    ride_hailing_order: Opt[RideHailingOrderRef] = None


class RideHailingPartnerRequest(
    RideHailingPRContent,
    TripPartnerRequest,
):
    """网约车搭子请求"""

    # TODO 覆盖原有字段实例，需要重新声明 dump_flags，建议添加可继承版的实例声明
    type: FieldT[PartnerRequestL2Type] = field(
        default=PartnerRequestL2Type.RIDE_HAILING,
        dump_flags={
            "managed",
        },
    )


class RideHailingPREditable(
    PartnerRequestEditable,
    RideHailingPartnerRequest,
):
    """网约车搭子请求可编辑内容"""
