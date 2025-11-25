"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 接口响应数据模型
issues: 
    #2
references: 

"""

# typing
from dataclasses import dataclass
from backend_common.schemas.serializers import as_str_serializer
from typing import List, Optional, TypeVar, Generic, Annotated
from pydantic import BaseModel, RootModel, field_validator, Field


ResponseBodyDataType = TypeVar("ResponseBodyDataType")
class ResponseBody(BaseModel, Generic[ResponseBodyDataType]):

    """
    曹操出行通用API响应
    """
    code: int
    success: Optional[bool] = False
    msg: Optional[str] = None
    data: Optional[ResponseBodyDataType] = None


from app.schemas.service_provider.caocao.availiablity import CityAvailability
class getAllCitiesData(BaseModel):

    """
    城市服务开通状态的响应

    https://app.apifox.com/link/project/5283937/apis/api-224155442
    """
    cities: List[CityAvailability]

class queryCityData(BaseModel):

    """
    城市编码查询（根据经纬度）

    https://app.apifox.com/link/project/5283937/apis/api-224206252
    """
    city_code: str

'''queryMeterRuleData'''
from app.schemas.service_provider.caocao.config import CaocaoCarType
@dataclass
class dateTimeInterval:
    end: Optional[str] = None
    price: Optional[int] = None
    start: Optional[str] = None

@dataclass
class festivalFeeVo:
    category: int
    dateTimeIntervals: List[dateTimeInterval]
    name: str

@dataclass
class FeeVo:
    basePrice: int
    desc: str

@dataclass
class startPriceVo(FeeVo):
    startInclueKm: float
    startIncludeMinute: int

@dataclass
class longWayFeeVo(FeeVo):
    longWayStart: int

@dataclass
class nightFeeVo(FeeVo):
    nightStart: str
    nightEnd: str
    nightIncludeKm: float
    nightStartPrice: int

class queryMeterRuleData(BaseModel):

    """
    查询计价规则

    https://app.apifox.com/link/project/5283937/apis/api-224214119
    """
    carTypeCode: CaocaoCarType
    carTypeDesc: str
    remark: str
    cityCode: str
    startPrice: startPriceVo
    longWay: longWayFeeVo
    timePrice: FeeVo
    kmPrice: FeeVo
    nightFee: nightFeeVo
    festivalFeeVo: Optional[festivalFeeVo]
'''/queryMeterRuleData'''

'''estimatePriceData'''
from app.schemas.service_provider.caocao.price import CaocaoPriceDetail, CaocaoLineType
class estimatePriceDetail(BaseModel):
    name: str
    originPrice: int
    '''
    预估价格打折前原价

    允许拼车时为未拼车一口价
    '''
    price: int
    '''
    预估价格
    
    允许拼车时为拼成一口价
    '''
    priceKey: str
    '''
    有效期10分钟；过期或路线变化需要重新预估
    '''
    routeStrategy: int
    carType: CaocaoCarType
    carpoolFlag: bool
    carpoolType: int
    derateType: int
    '''
    折扣类型
    
    1: 企业折扣 2: 动态折扣
    '''
    distance: int
    duration: int
    donateActivityAmount: int
    doubleHighSpeedFeeFlag: int
    '''
    0：正常收取高速费
    '''
    lineType: CaocaoLineType
    '''
    线路类型

    0: 普通类型；1: 一口价类型
    '''
    dynamicRuleId: int
    '''
    动态折扣ID；仅在动态折扣为2时才有值

    下单时需透传
    '''
    detail: List[CaocaoPriceDetail]

class estimatePriceWithDetailResponseData(RootModel):

    """
    预估价格带明细

    https://app.apifox.com/link/project/5283937/apis/api-224225061
    """
    root: List[estimatePriceDetail] = []

'''/estimatePriceData'''

'''orderCar'''
class orderCarResponseData(BaseModel):
    orderNo: str

    @field_validator("orderNo", mode="before")
    def order_no_validator(v):
        return str(v)

'''/orderCar'''

'''queryOrderDetail'''
from app.schemas.service_provider.caocao import CaocaoOrder
class queryOrderDetailResponseData(CaocaoOrder):

    """
    查询订单详情

    https://app.apifox.com/link/project/5283937/apis/api-224285481
    """

    pass
'''/queryOrderDetail'''

'''cancelOrder'''
class cancelOrderResponseData(BaseModel):

    """
    取消订单

    https://app.apifox.com/link/project/5283937/apis/api-224275638
    """
    orderNo: str
    cancelFee: int

    @field_validator("orderNo", mode="before")
    def order_no_validator(v):
        return str(v)

'''/cancelOrder'''

'''queryCancelFee'''
class queryCancelFeeResponseData(cancelOrderResponseData):

    """
    查询取消费用

    https://app.apifox.com/link/project/5283937/apis/api-224329887
    """
'''/queryCancelFee'''


'''queryDriverPolyline'''
from app.schemas.service_provider.caocao.route import CaocaoStep, CaocaoETAInfo
class queryDriverPolylineResponseData(BaseModel):

    """
    查询司机路线

    https://app.apifox.com/link/project/5283937/apis/api-224330042
    """
    driverNo: int = 0
    navigationPolylineType: int = 1
    """路线类型 1-接客路线 2-等客状态 3-送客路线"""
    steps: List[CaocaoStep] = Field(default_factory=list)
    driverEtaInfoVO: CaocaoETAInfo

'''/queryDriverPolyline'''

'''queryDriverLocation'''
class queryDriverLocationResponseData(BaseModel):

    """
    查询司机位置

    https://app.apifox.com/link/project/5283937/apis/api-224319606    
    """
    direction: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0

'''/queryDriverLocation'''
