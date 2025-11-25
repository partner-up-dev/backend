"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 API请求数据模型
issues: 

references: 

"""

from backend_common.schemas.serializers import enum_serializer
from enum import IntEnum
from typing import List, Optional, Annotated
from pydantic import BaseModel, Field, field_serializer

# typing - business module
from app.schemas.service_provider.caocao import CaocaoOrderType
from app.schemas.service_provider.caocao.config import CaocaoCarType, CaocaoSMSPolicy
from app.schemas.service_provider.caocao.price import CaocaoLineType, CaocaoOrderTag
from app.schemas.service_provider.caocao.base import OnOff

# utils
import json


'''estmatePriceWithDetail'''
class estimatePriceWithDetailRequestData(BaseModel):

    """
    预估价格带明细Query
    """
    car_type: str
    """允许多种车型；使用逗号分隔"""
    city_code: str
    """城市编码（与起点对应的citycode保持一致）"""
    from_latitude: float
    from_longitude: float
    order_type: Annotated[CaocaoOrderType, enum_serializer]
    to_latitude: float
    to_longitude: float
    carpool_type: Annotated[Optional[OnOff], enum_serializer] = OnOff.OFF
    """是否允许拼车：0 不拼车；1 允许拼车，默认为不拼车"""
    count_person: Optional[int] = None
    """拼车乘车人数，允许拼车时必填，必须为1或2"""
    departure_time: Optional[str] = None
    """出发时间；格式：yyyy-MM-dd HH:mm:ss；非实时单必填；"""
    order_tags: Optional[int] = None
    """尊享一口价时才需要传递，值为 1 （尊享一口价需与商务确认开通权限）"""
    passenger_phone: Optional[str] = None
    """乘客手机号"""


'''/estmatePriceWithDetail'''

'''orderCar'''
class serviceTypePrice(BaseModel):

    """
    服务类型价格，用于多车型叫车

    https://app.apifox.com/link/project/5283937/apis/schema-125475203
    """
    serviceType: Annotated[CaocaoCarType, enum_serializer]
    estimateKey: str
    estimatePrice: int
    fixLineType: Optional[int] = None


class orderCarRequestData(BaseModel):

    ext_order_id: str
    """外部订单号"""
    car_type: Annotated[Optional[CaocaoCarType], enum_serializer] = None
    """多车型同时呼叫可以不传"""
    ext_uid: Optional[str] = None

    from_latitude: float
    from_longitude: float
    start_poi_id: Optional[str] = None
    """开始点POI (高德地图)"""
    end_poi_id: Optional[str] = None
    """结束点POI (高德地图)"""
    to_latitude: Optional[float] = None
    """（订单类型为日租、半日租时，目的地经纬度参数非必传）"""
    to_longitude: Optional[float] = None
    """（订单类型为日租、半日租时，目的地经纬度参数非必传）"""
    order_longitude: Optional[float] = None
    """下单位置经度"""
    order_latitude: Optional[float] = None
    """下单位置纬度"""

    caller_phone: str
    passenger_phone: Optional[str] = None
    passenger_hide_phone: Optional[str] = None
    """乘车人脱敏手机号，依赖手机号后四位用于司机端展示，便于司乘确认身份（传入乘客虚拟号的接入方该字段必传）"""
    passenger_name: Optional[str] = None

    estimate_price: Optional[int] = None
    estimate_price_key: Optional[str] = None
    city_code: str
    order_type: Annotated[CaocaoOrderType, enum_serializer]

    start_name: str
    start_address: str = Field(max_length=100)
    end_name: str
    end_address: str = Field(max_length=100)

    dynamic_rule_id: Optional[str] = None
    order_tags: Annotated[Optional[CaocaoOrderTag], enum_serializer] = None
    line_type: Annotated[Optional[CaocaoLineType], enum_serializer] = None
    accept_cp_driver: Annotated[Optional[OnOff], enum_serializer] = None
    accept_relay_order: Annotated[Optional[OnOff], enum_serializer] = None
    carpool_type: Annotated[Optional[OnOff], enum_serializer] = None
    count_person: Optional[int] = Field(default=None, max=2, min=1)

    flight_no: Optional[str] = None
    flt_takeoff_time: Optional[str] = None
    """格式:yyyy-MM-dd HH:mm:ss"""

    departure_time: Optional[str] = None
    """预约单必填(格式:yyyy-MM-dd HH:mm:ss)"""

    sms_policy: Annotated[Optional[CaocaoSMSPolicy], enum_serializer] = CaocaoSMSPolicy.BOTH
    extra_info: Optional[str] = None
    '''展示给司机的订单备注信息'''
    callback_info: Optional[str] = None
    '''状态通知回调参数'''   

    is_simultaneously_call: Annotated[Optional[OnOff], enum_serializer] = OnOff.ON
    '''是否多车型呼叫'''
    service_type_price: Optional[List[serviceTypePrice]] = None
    """
    多车型同时呼叫车型、预估价格和预估key的对应信息，
    序列化为json格式的str
    """

    @field_serializer("service_type_price")
    def serialize_service_type_price(value: List[serviceTypePrice]) -> str:
        return json.dumps(
            [item.model_dump(exclude_unset=True) for item in value]
        )


'''/orderCar'''

'''queryOrderDetail'''
class queryOrderDetailRequestData(BaseModel):
    order_id: str
    """曹操出行订单ID"""

'''/queryOrderDetail'''

'''cancelOrder'''
from app.schemas.order import (
    PassengerCancelReason, PlatformCancelReason, RideHailingOrderCancelReason
)
from app.schemas.service_provider.caocao import CaocaoCancelCode
class whoCancel(IntEnum):

    """
    取消方
    """
    PASSENGER = 1
    PLATFORM = 2

    @classmethod
    def from_standard_cancel_code(cls, code: RideHailingOrderCancelReason) -> 'whoCancel':

        """
        从标准取消原因转换
        """
        if isinstance(code, PassengerCancelReason):
            return cls.PASSENGER
        elif isinstance(code, PlatformCancelReason):
            return cls.PLATFORM
        else:
            raise ValueError(f"Unsupported cancel code {code}")

class cancelOrderRequestData(BaseModel):

    order_id: str
    """曹操出行订单ID"""
    cancel_code: Annotated[CaocaoCancelCode, enum_serializer]
    """取消原因代码"""
    cancel_reason: str
    """取消原因详情"""
    who_cancel: Annotated[Optional[whoCancel], enum_serializer] = None
    """取消方"""

'''/cancelOrder'''

'''queryCancelFee'''
class queryCancelFeeRequestData(BaseModel):
    order_no: str
    """曹操出行订单ID"""

'''/queryCancelFee'''

'''feeConfirm'''
class feeConfirmRequestData(BaseModel):
    order_id: str
    """曹操出行订单ID"""
    allowance_amount: Optional[int] = None
    """第三方平台补贴金额，分"""
    cao_allowance_amount: Optional[int] = None
    """曹操分摊补贴金额，分"""

'''/feeConfirm'''

'''queryDriverPolyline'''
class navigationPolylineType(IntEnum):

    """
    曹操queryDriverPolyline可用的导航路线类型
    """
    PICKING_UP = 1
    """接乘客"""
    WAITING = 2
    """等乘客"""
    DROPPING_OFF = 3
    """送乘客"""

class queryDriverPolylineRequestData(BaseModel):
    order_id: str
    """曹操出行订单ID"""
    navigationPolylineType: Annotated[navigationPolylineType, enum_serializer]
'''/queryDriverPolyline'''

'''queryDriverLocation'''
class queryDriverLocationRequestData(BaseModel):
    order_id: str
    """曹操出行订单ID"""
'''/queryDriverLocation'''
