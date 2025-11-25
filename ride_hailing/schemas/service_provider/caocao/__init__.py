"""
author: Lan_zhijiang
date: 2024-10-17
desc: 曹操出行模块的主要数据模型
issues: 
    #2
references: 

"""

from typing import Dict, List, Literal, Optional
from enum import IntEnum
from backend_common.schemas import BaseSchema
from pydantic import BaseModel, Field, field_validator, model_validator

# typing - business module
from app.schemas.service_provider import ServiceProviderOrderStatus, ServiceProviderOrder
from app.schemas.service_provider.caocao.base import OnOff
from app.schemas.order.config import Purpose, RideHailingPreference
from app.schemas.service_provider.caocao.config import CaocaoCarType
from app.schemas.service_provider.caocao.price import CaocaoPriceDetail
from app.schemas.order import (
    RideHailingOrderType, 
    RideHailingOrderCancelReason, PlatformCancelReason, PassengerCancelReason, DriverCancelReason,
    RideHailingOrderStatus
)

# libs
from app.libs.exceptions import ParamsInvalid

# utils
from app.utils.base import if_none_then_default


class CaocaoOrderType(IntEnum):

    INSTANT = 1
    SCHEDULED = 2
    AIRPORT_PICKUP = 3
    AIRPORT_DROPOFF = 4
    RENTAL_DAILY = 5
    RENTAL_HALF_DAY = 6

    @classmethod
    def from_preference(cls, preference: RideHailingPreference | None) -> 'CaocaoOrderType':
        
        """
        从RideHailingPrefernece计算订单类型

        :param preference: RideHailingPreference

        """
        if preference is None:
            return cls.INSTANT

        if preference.purpose == Purpose.AIRPORT_DROPOFF:
            return cls.AIRPORT_DROPOFF
        elif preference.purpose == Purpose.AIRPORT_PICKUP:
            return cls.AIRPORT_PICKUP
        elif preference.purpose in [Purpose.RAILWAY_DROPOFF, Purpose.RAILWAY_PICKUP]:
            # 接送站不支持，不能产生误解
            raise ParamsInvalid("preference purpose", preference.purpose, "Not Railway")
        elif preference.purpose == Purpose.SELF_DRIVE:
            rental_duration = if_none_then_default(preference.rental_duration, 0)
            if rental_duration > 12:
                # WARN 大于24小时应该算一天吗？
                return cls.RENTAL_DAILY
            elif rental_duration < 1:
                raise ParamsInvalid("preference rental_duration", rental_duration, "can't less than 1h")
            else:
                return cls.RENTAL_HALF_DAY
        
        # COMMON, COMMUTE(暂无处理)
        return cls.INSTANT

    @classmethod
    def from_standard(
        cls, order_type: RideHailingOrderType, 
        reservable: bool = True
    ):

        """
        从标准网约车订单类型获取曹操订单类型

        :param reservable: bool 是否可预约；默认可以，如果实际不行则曹操会驳回，不会导致误打车的问题

        注意接送站没有对应的类型，所以会根据是否可预定，fallback到预定单或实时单
        """
        if order_type == RideHailingOrderType.INSTANT:
            return cls.INSTANT
        elif order_type == RideHailingOrderType.SCHEDULED:
            return cls.SCHEDULED
        elif order_type == RideHailingOrderType.AIRPORT_PICKUP:
            return cls.AIRPORT_PICKUP
        elif order_type == RideHailingOrderType.AIRPORT_DROPOFF:
            return cls.AIRPORT_DROPOFF
        elif order_type == RideHailingOrderType.RENTAL_DAILY:
            return cls.RENTAL_DAILY
        elif order_type == RideHailingOrderType.RENTAL_HALF_DAY:
            return cls.RENTAL_HALF_DAY
        elif order_type == RideHailingOrderType.RAILWAY_PICKUP or order_type == RideHailingOrderType.RAILWAY_DROPOFF:
            if reservable:
                return cls.SCHEDULED
        
        return cls.INSTANT

    @property
    def is_reserving(self) -> bool:

        """
        该类型是否为预约单
        """

        return self in [
            CaocaoOrderType.SCHEDULED, CaocaoOrderType.AIRPORT_PICKUP, CaocaoOrderType.AIRPORT_DROPOFF,
            CaocaoOrderType.RENTAL_DAILY, CaocaoOrderType.RENTAL_HALF_DAY
        ]

class CaocaoOrderStatus(ServiceProviderOrderStatus, IntEnum):

    UNASSIGNED = 1
    '''未派单, 订单尚未分配给司机'''
    ASSIGNED = 2
    '''已派单, 订单已分配给司机'''
    PASSENGER_ONBOARD = 3
    '''乘客上车，计费开始, 乘客已上车，开始计费'''
    TRIP_ENDED = 8
    '''行程结束，计费结束, 行程结束，计费停止'''
    PENDING_PAYMENT = 5
    '''订单待支付, 订单已完成，等待乘客支付'''
    PENDING_REVIEW = 7
    '''订单已支付，待评价, 订单已支付，等待乘客评价'''
    REVIEWED = 6
    '''订单已评价, 订单已完成并评价'''
    SYSTEM_CANCELLED = 4
    '''订单系统取消（超时无司机接单或预约单改派失败）, 系统自动取消订单'''
    SERVICE_STARTED = 9
    '''开始服务, 司机出发接乘客'''
    CANCELLED_PENDING_PAYMENT = 10
    '''订单取消，待付款, 订单被取消，等待付款处理'''
    REASSIGNING = 11
    '''订单改派中（预约单才有）, 预约单正在改派给其他司机'''
    DRIVER_ARRIVED = 12
    '''司机已到达, 司机已到达乘客指定地点'''
    CANCELLED_PAID = 13
    '''订单取消已支付, 订单被取消，乘客已支付'''
    CANCELLED_NO_FEE = 14
    '''订单取消已免责取消费, 订单被取消，免责取消费'''
    USER_CANCELLED = 20
    '''用户取消, 乘客取消订单'''
    CUSTOMER_SERVICE_CANCELLED = 21
    '''客服取消, 客服取消订单'''
    DRIVER_CANCELLED = 26
    '''司机取消, 司机取消订单'''
    THIRD_PARTY_CANCELLED = 27
    '''第三方取消, 第三方取消订单'''

    def to_standard(self):

        c = CaocaoOrderStatus
        
        if self == c.UNASSIGNED or self == c.REASSIGNING:
            return RideHailingOrderStatus.DISPATCHING
        if self == c.ASSIGNED:
            return RideHailingOrderStatus.ACCEPTED
        if self == c.SERVICE_STARTED:
            return RideHailingOrderStatus.PICKING_UP
        if self == c.DRIVER_ARRIVED:
            return RideHailingOrderStatus.ARRIVED
        if self == c.PASSENGER_ONBOARD:
            return RideHailingOrderStatus.IN_PROGRESS
        if self == c.TRIP_ENDED:
            return RideHailingOrderStatus.DROPPED
        if self == c.PENDING_PAYMENT or self == c.CANCELLED_PENDING_PAYMENT:
            return RideHailingOrderStatus.UNPAID
        if self == c.PENDING_REVIEW:
            return RideHailingOrderStatus.REVIEW_OPENING
        if self == c.REVIEWED:
            return RideHailingOrderStatus.CLOSED
        if self in (
            c.SYSTEM_CANCELLED, c.DRIVER_CANCELLED,
            c.CUSTOMER_SERVICE_CANCELLED, c.USER_CANCELLED,
            c.THIRD_PARTY_CANCELLED, c.CANCELLED_NO_FEE,
            c.CANCELLED_PAID
        ):
            return RideHailingOrderStatus.CANCELLED

class CaocaoOrderOrigin(IntEnum):

    '''
    曹操订单来源
    '''
    OPEN_API = 1
    PERSONAL_H5 = 2
    ENTERPRISE_H5 = 3
    INVITATION_H5 = 4
    PUBLIC_SERVANT_CLIENT = 5
    APP = 6
    ENTERPRISE_CONSOLE = 7
    CUSTOMER_SERVICE = 8
    OTHER = 0

class CaocaoOrderPersonalPayMethod(IntEnum):

    '''
    曹操订单个人支付部分的支付方式
    '''
    CASH = 3
    ALIPAY = 2
    WECHAT = 5
    WALLET = 8
    NONE = 0

class WaypointInfo(BaseModel):

    orderNo: str
    startLng: float
    startLat: float
    endLng: float
    endLat: float
    countPerson: int
    status: CaocaoOrderStatus


'''CaocaoOrder'''
class basicOrderVO(BaseModel):

    accid: Optional[str] = None
    '''用车H5传入的第三方用户ID'''
    acceptCPDriver: bool
    '''下单时是否允许加盟运力'''
    cpDriver: bool = False
    '''实际是否为加盟运力'''
    carpoolType: OnOff = OnOff.OFF
    '''下单时是否允许拼车'''
    carpoolFlag: OnOff = OnOff.OFF
    '''是否拼成'''
    carpoolOrder: Optional[str] = None
    '''拼车订单号'''
    countPerson: Optional[int] = None
    '''拼车单乘车人数'''
    isRelayOrder: bool = False
    '''是否为接力单'''
    preOrderEndFlag: bool = False
    '''接力单状态：上一单是否结束'''
    preOrderEndLocation: Optional[Dict[Literal['longitude', 'latitude'], float]] = None
    callerPhone: str
    '''打车人手机号'''
    callbackInfo: str
    '''回调信息'''
    cityCode: str
    '''城市编码'''
    companyNo: int = 0
    '''公司编号'''
    orderTime: str
    '''下单时间'''
    departureTime: str
    '''出发时间'''
    striveTime: Optional[str] = None
    '''司机接单时间'''
    arrivedTime: Optional[str] = None
    '''司机到达时间'''
    startServiceTime: Optional[str] = None
    '''开始服务时间'''
    beginChargeTime: Optional[str] = None
    '''开始计费时间'''
    finishTime: Optional[str] = None
    '''订单结束时间'''
    payTime: Optional[str] = None
    '''支付时间'''
    canceledTime: Optional[str] = None
    '''订单取消时间'''
    normalTime: Optional[int] = None
    '''实际行驶时间'''
    normalDistance: Optional[float] = None
    '''实际行驶里程 千米'''
    nightTime: Optional[int] = None
    '''夜间行驶时间'''
    nightKm: Optional[float] = None
    '''夜间行驶里程 千米'''
    longKm: Optional[float] = None
    '''长途行驶里程 千米'''
    endAddress: str
    endName: str
    startAddress: str
    startName: str
    estimatePrice: int
    '''预估价格'''
    extOrderId: str
    '''外部订单ID'''
    extraInfo: str
    '''额外信息'''
    fromLocation: Dict[Literal['lat', 'lng'], float]
    toLocation: Dict[Literal['lat', 'lng'], float]
    orderLocation: Dict[Literal['lat', 'lng'], float]
    realStartLocation: Optional[Dict[Literal['latitude', 'longitude', 'direction'], float]] = None
    realEndLocation: Optional[Dict[Literal['latitude', 'longitude', 'direction'], float]] = None
    invoiceStatus: OnOff = OnOff.OFF
    invoiced: bool = False
    orderId: str
    origin: CaocaoOrderOrigin = CaocaoOrderOrigin.OTHER
    '''订单来源'''
    passengerName: Optional[str] = None
    '''乘客姓名'''
    passengerPhone: Optional[str] = None
    '''乘客手机号'''
    personalPayMethod: CaocaoOrderPersonalPayMethod = CaocaoOrderPersonalPayMethod.NONE
    '''订单个人支付部分使用支付方式'''
    requireLevel: CaocaoCarType
    routeFixedPrice: bool = False
    '''是否路线一口价'''
    specialFixedPrice: bool = False
    '''是否尊享一口价'''
    status: CaocaoOrderStatus
    '''订单状态'''
    type: CaocaoOrderType = CaocaoOrderType.INSTANT
    '''订单类型'''
    ruleId: int = 0
    '''用车规则ID'''
    situationName: Optional[str] = None
    '''用车场景名称'''
    companyReason: Optional[str] = None
    '''用车备注'''
    wayPointInfoList: List[WaypointInfo] = list
    '''拼车单途经点（子订单）信息'''
    allowModifyDest: bool = False
    '''是否允许修改目的地'''

    @field_validator("orderId", mode="before")
    def validate_order_id(value) -> str:
        return str(value)

class driverInfoVO(BaseModel):

    avatar: Optional[str] = None
    carType: str
    '''车辆型号'''
    carBrand: str
    '''车辆品牌'''
    carSeats: int = 2
    '''车辆座位数'''
    card: str
    '''车牌号'''
    color: str
    '''车辆颜色'''
    id: int
    '''司机编号'''
    level: str
    '''司机服务评分'''
    name: str = ""
    '''司机姓名'''
    orderCnt: int = 0
    '''司机接单数'''
    phone: str
    '''司机与打车人手机号（虚拟）'''
    phonePassenger: Optional[str] = None
    '''司机与乘客之间的手机号（虚拟）'''
    location: Optional[Dict[Literal['lat', 'lng'], float]] = None
    '''司机位置'''

class orderFeeVO(BaseModel):

    companyPayAmount: Optional[int] = None
    '''
    企业支付的总金额
    
    改价前支付金额+改价后补扣和退款的金额；\n
    企业支付后才会有值
    '''
    personalPayAmount: Optional[int] = None
    '''个人支付部分'''
    originTotalFee: Optional[int] = None
    '''
    订单折前原价金额
    
    如订单无实际行程无值则不返回该字段
    '''
    totalFee: Optional[int] = None
    '''
    折后订单总金额
    
    支付前改价则是改价后的价格
    '''
    doubleTollFlag: Optional[int] = None
    '''
    当预估路线存在高速路段时

    0 代表高速费正常收取。
    其中一口价类型订单高速费直接计入一口价内，普通类型价订单不计入预估价，仅做提示
    '''
    detailFeeVos: List[CaocaoPriceDetail] = Field(default_factory=list)

class CaocaoOrder(ServiceProviderOrder[str]):

    basicOrderVO: basicOrderVO
    driverInfoVo: Optional[driverInfoVO] = None
    orderFeeVo: orderFeeVO

    @model_validator(mode='after')
    def validate_id(self, values):

        if not self.id:
            self.id = self.basicOrderVO.orderId


'''/CaocaoOrder'''


class CaocaoCancelCode(IntEnum):

    """
    曹操出行取消原因代码
    """
    TRIP_CHANGED = 1
    '''行程有变化, 乘客'''
    MISTAKE = 2
    '''误操作, 乘客'''
    DRIVER_UNAVAILABLE = 3
    '''司机来不了, 乘客'''
    DRIVER_TOO_FAR = 4
    '''司机太远，不愿等待, 乘客'''
    DRIVER_RESTRICTED = 5
    '''司机限号/堵车无法到来, 乘客'''
    DRIVER_UNWILLING = 6
    '''司机不愿意来, 乘客'''
    OTHER = 8
    '''其它, 乘客'''
    NO_REASON = 12
    '''用户无理由取消, 乘客'''
    AGREED_WITH_DRIVER = 13
    '''与司机协商后取消, 乘客'''
    DRIVER_UNREACHABLE = 14
    '''联系不上司机, 乘客'''
    DRIVER_LATE = 15
    '''司机迟到, 乘客'''
    DRIVER_POOR_ATTITUDE = 16
    '''司机服务态度差, 乘客'''
    DRIVER_CANNOT_FIND = 17
    '''司机找不到我, 乘客'''
    BIDDING_TIMEOUT = 18
    '''竞单超时, 第三方平台'''
    BIDDING_FAILED = 19
    '''竞单失败, 第三方平台'''
    BIDDING_ACCESS_FAILED = 20
    '''竞单准入失败, 第三方平台'''
    BIDDING_RISK_CONTROL = 21
    '''竞单风控, 第三方平台'''
    DRIVER_NOT_QUALIFIED = 24
    '''司机不符合接单条件, 第三方平台'''
    PASSENGER_NO_USE = 25
    '''乘客未使用换舱取消, 第三方平台'''

    @classmethod
    def from_standard(cls, standard: RideHailingOrderCancelReason) -> 'CaocaoCancelCode':

        if standard == PassengerCancelReason.ROUTE_CHANGED:
            return cls.TRIP_CHANGED
        if standard == PassengerCancelReason.CONSENSUAL:
            return cls.AGREED_WITH_DRIVER
        if standard == PassengerCancelReason.NO_REASON:
            return cls.NO_REASON
        if standard == PassengerCancelReason.PICKUP_LATE:
            return cls.DRIVER_LATE
        if standard == PassengerCancelReason.DRIVER_UNREACHABLE:
            return cls.DRIVER_UNREACHABLE
        if standard == PassengerCancelReason.ACCIDENTAL:
            return cls.MISTAKE
        
        if standard == PlatformCancelReason.OTHER_SERVICE_PROVIDER_SELECTED:
            return cls.BIDDING_FAILED
        if standard == PlatformCancelReason.PAYMENT_TIMEDOUT:
            # this shoul be unreachable
            return cls.BIDDING_RISK_CONTROL
        
        return cls.OTHER
