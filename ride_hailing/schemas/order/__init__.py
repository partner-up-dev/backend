"""
author: Lan_zhijiang
date: 2024-10-16
desc: 网约车订单模块的核心数据模型
issues: 

references: 

"""

__module_name__ = "OrderSchema"

# typing
import datetime
from enum import Enum
from pydantic import Field, field_serializer
# from app.schemas import BaseSchema, enum_serializer, TranslatableEnum
from backend_common.schemas import BaseSchema, BaseCommonSchema
from backend_common.schemas.serializers import enum_serializer, as_str_serializer
from backend_common.libs.i18n import TranslatableEnum
from typing import Annotated, Dict, List, Literal, Optional, Union, Iterable

# i18n
from backend_common.libs import i18n
t = i18n.get_translator(__module_name__, localedir="data/locales")
de_p = i18n.pgettext_placeholder

# schemas
from app.schemas.service_provider import ServiceProvider
from app.schemas.order.price import RideHailingOrderFareType, PriceInfo
from app.schemas.order.config import RideHailingPreference
from app.schemas.base.route import Route


class RideHailingOrderStatus(Enum):

    """
    网约车订单状态

    https://app.apifox.com/link/project/5303644/apis/schema-125225386
    """

    PENDING = "pending"
    '''还未提交到服务供应商'''
    DISPATCHING = "dispatching" # 正在派单
    COMPETING = "competing" # 正在竞争
    ACCEPTED = "accepted" # 司机接单
    PICKING_UP = "picking_up" # 司机正在前往接客
    ARRIVED = "arrived" # 司机已到达上车点
    PICKED = "picked" # 接到乘客
    IN_PROGRESS = "in_progress" # 行程中
    DROPPED = "dropped" # 到达目的地
    UNPAID = "unpaid" # 有款项未支付
    REVIEW_OPENING = "review_opening" # 可以评价
    CLOSED = "closed" # 订单结束（正常关闭）
    CANCELLED = "cancelled" # 订单取消
    ERROR = "error" # 订单异常

class RideHailingOrderType(Enum):

    """
    网约车订单类型

    https://app.apifox.com/link/project/5303644/apis/schema-125226083
    """
    INSTANT = "instant" # 即时用车
    SCHEDULED = "scheduled" # 预约用车
    AIRPORT_PICKUP = "airport_pickup" # 接机
    AIRPORT_DROPOFF = "airport_dropoff" # 送机
    RAILWAY_PICKUP = "railway_pickup" # 接站
    RAILWAY_DROPOFF = "railway_dropoff" # 送站
    RENTAL = "rental" # 租车

    @property
    def is_reserving(self) -> bool:

        """
        是否为预约单
        """

        return self in [
            self.SCHEDULED, self.AIRPORT_PICKUP, self.AIRPORT_DROPOFF, 
            self.RAILWAY_PICKUP, self.RAILWAY_DROPOFF
        ]

''' CancelReason '''

class PassengerCancelReason(TranslatableEnum):

    """
    乘客方导致的取消订单原因代码
    """
    def __init__(self, *args):
        super().__init__(t, "user_cancel_reason")

    ROUTE_CHANGED = de_p("user_cancel_reason", "route_changed") 
    '''路线变更'''
    CONSENSUAL = de_p("user_cancel_reason", "consensual")
    '''双方协商一致'''
    NO_REASON = de_p("user_cancel_reason", "no_reason")
    '''无理由'''
    PICKUP_LATE = de_p("user_cancel_reason", "pickup_late") 
    '''司机迟到'''
    DRIVER_UNREACHABLE = de_p("user_cancel_reason", "driver_unreachable") 
    '''司机联系不上'''
    ACCIDENTAL = de_p("user_cancel_reason", "accidental")
    '''误操作'''
    PARTNER_REJECTED = de_p("user_cancel_reason", "partner_rejected")
    '''乘车人（搭子）拒绝'''

class PlatformCancelReason(TranslatableEnum):

    """
    我方（平台方）导致的取消订单原因代码
    """
    def __init__(self, *args):
        super().__init__(t, "platform_cancel_reason")

    OTHER_SERVICE_PROVIDER_SELECTED = de_p("platform_cancel_reason", "other_service_provider_selected")
    '''选择了其它服务供应商'''
    PAYMENT_TIMEDOUT = de_p("platform_cancel_reason", "payment_timedout")
    '''需要预支付或授权自动扣款，但是超时未完成'''
    COMPETITORS_EXPIRD = de_p("platform_cancel_reason", "competitors_expired")
    '''所有竞争者都过期了（价格信息过期）'''
    COMPETITORS_UNRESPONSIVE = de_p("platform_cancel_reason", "competitors_unresponsive")
    '''所有竞争者都无司机接单'''

class ServiceProviderCancelReason(TranslatableEnum):

    """
    服务供应商方导致的取消订单原因代码
    """
    def __init__(self, *args):
        super().__init__(t, "service_provider_cancel_reason")

class DriverCancelReason(TranslatableEnum):

    """
    司机方导致的取消订单原因代码
    """
    def __init__(self, *args):
        super().__init__(t, "driver_cancel_reason")

    PASSENGER_UNREACHABLE = de_p("driver_cancel_reason", "passenger_unreachable")
    '''乘客联系不上'''


RideHailingOrderCancelReason = Union[
    PassengerCancelReason, PlatformCancelReason, ServiceProviderCancelReason, DriverCancelReason
]
"""
网约车订单取消原因

是聚合类型，可以通过 isinstance 判断更具体的原因分类

https://app.apifox.com/link/project/5303644/apis/schema-125338089
"""

''' /CancelReason '''

class DriveInfo(BaseCommonSchema):

    """
    行使信息

    https://app.apifox.com/link/project/5303644/apis/schema-125303035
    """
    distance: Optional[int] = None
    '''实际行驶里程'''
    duration: Optional[int] = None
    '''实际行驶时间'''


RideHailingOrderTimelineKeys = Literal[
    'order', 'dispatch', 'accept', 'arrive',
    'start_service', 'departure', 'begin_charge', 'drop', 'end_service',
    'pay', 'cancel'
]
"""
网约车订单时间记录类型
"""

class Competitor(PriceInfo):

    """
    竞争者

    记录车型+价格+订单信息
    """

    service_provider_order_id: str | None = None

    def update_price_info(self, price_info: PriceInfo):

        """
        更新价格信息数据
        """
        self.update_from_dict(**price_info.dump_as_dict())

class RideHailingOrder(BaseSchema[int]):

    """
    网约车订单

    https://app.apifox.com/link/project/5303644/apis/schema-125225331
    """
    service_provider_order_id: Annotated[str | None, as_str_serializer] = None
    status: Annotated[RideHailingOrderStatus, enum_serializer] = RideHailingOrderStatus.PENDING
    type: Annotated[RideHailingOrderType, enum_serializer]
    fare_type: Annotated[RideHailingOrderFareType | None, enum_serializer] = None
    ride_type: str | None = None  # ref to RideType
    passengers: List[str] = Field(default_factory=list, min_length=1)
    drive: DriveInfo = Field(default_factory=DriveInfo)
    route: Route
    timeline: Dict[RideHailingOrderTimelineKeys, datetime.datetime] = Field(default_factory=dict)
    cancel_reason: Annotated[RideHailingOrderCancelReason | None, enum_serializer] = None
    cancelled_by: str | None = None
    '''取消发起者'''
    partner_request: int | None = None
    split_bill: int | None = None
    preference: RideHailingPreference | None = None
    '''打车偏好'''
    competitors: Dict[ServiceProvider, List[Competitor]] = dict
    '''
    竞争者信息（多服务提供商打车信息）

    key为service_provider_id，值为ride_type的列表；

    处于Draft状态的订单，competitiors代表应当下单的车型
    '''

class DriverInfo(BaseCommonSchema):

    """
    司机信息

    用于前端查询，不会存储在后端
    """
    name: str
    '''司机姓名'''
    avatar: Optional[str] = None
    '''司机头像地址；前端注意放行'''
    phones: Iterable[str] = Field(default_factory=list, min_length=1)
    '''
    与司机联系的电话号码列表

    与订单乘客列表顺序对应
    '''
    auto_brand: str
    '''车辆品牌'''
    auto_model: str
    '''车辆型号'''
    auto_color: str
    '''车辆颜色'''
    auto_plate: str
    '''车牌号'''

