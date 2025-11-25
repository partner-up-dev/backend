"""通勤搭子请求数据模型"""

import typing
import datetime
from typing import Optional as Opt
from blue_firmament.exceptions import AtLeastOne
from blue_firmament.scheme import field, FieldT, scheme_validator, EditableScheme
from ..base import PartnerRequestL2Type
from .ride_hailing import RideHailingOrderRef
from .base import TripPRContent, TripPartnerRequest
from ...base import Weekday
from dal import SupabaseAnonPostgrest


class CommutePRContent(
    TripPRContent, dal=SupabaseAnonPostgrest, dal_path=("commute", "partner_request")
):
    """通勤搭子请求特有内容"""

    on_at: Opt[datetime.time] = None
    """上班时间"""
    off_at: Opt[datetime.time] = None
    """下班时间"""
    workdays: FieldT[typing.List[Weekday]] = field(
        default_factory=lambda: [
            Weekday.MONDAY,
            Weekday.TUESDAY,
            Weekday.WEDNESDAY,
            Weekday.THURSDAY,
            Weekday.FRIDAY,
        ]
    )
    """工作日"""
    ride_hailing_orders: FieldT[typing.List[RideHailingOrderRef]] = field(default_factory=list)
    """网约车订单列表"""

    @scheme_validator
    def on_or_off(self):
        """
        on_at和off_at至少一个
        """
        if not self.on_at and not self.off_at:
            raise AtLeastOne("on_at", "off_at")


class CommutePartnerRequest(CommutePRContent, TripPartnerRequest):
    """通勤搭子请求"""

    type: FieldT[PartnerRequestL2Type] = field(
        default=PartnerRequestL2Type.COMMUTE,
        dump_flags={
            "managed",
        },
    )


class CommutePREditable(
    EditableScheme,
    CommutePartnerRequest,
    default_exclude_dump_flags={
        "managed",
    },
):
    """通勤搭子请求可编辑内容"""
