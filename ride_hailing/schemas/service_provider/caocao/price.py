"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 价格相关数据模型
issues: 
    #2
references: 

"""

from enum import Enum, IntEnum
from pydantic import BaseModel

# typing - business module
from app.schemas.order.price import RideHailingOrderFareType, PriceDetail, ChargeCode


class CaocaoChargeCode(Enum):

    """
    曹操出行费用代码
    """

    START_FEE = "start_fee"
    '''订单起步价'''
    TRAVEL_KM_FEE = "travel_km_fee"
    '''里程费用'''
    TRAVEL_MINUTE_FEE = "travel_minute_fee"
    '''时长费用'''
    LONG_KM_FEE = "long_km_fee"
    '''长途费'''
    LONG_KM2_FEE = "long_km2_fee"
    '''超远长途费'''
    NIGHT_FIX = "night_fix"
    '''夜间起步费用'''
    NIGHT_FEE = "night_fee"
    '''夜间行驶超长费用'''
    LOWEST_COST_FEE = "lowest_cost_fee"
    '''基础费用补充额（预约单基础费30元，例如一笔预约单初始预估18元，则基础费用补充额为12元）'''
    DISCOUNT_FEE = "discount_fee"
    '''折扣金额'''
    PARK_FEE = "park_fee"
    '''停车费用'''
    BRIDGE_FEE = "bridge_fee"
    '''路桥费'''
    CANCEL_FEE = "cancel_fee"
    '''取消费用'''
    OTHER_FEE = "other_fee"
    '''其他费用'''
    REFUND_FEE = "refund_fee"
    '''退款金额（客服改价/免单产生的退款金额）'''
    HIGHT_SPEED_FEE = "hight_speed_fee"
    '''高速费'''
    FESTIVAL_FEE = "festival_fee"
    '''节假日服务费'''
    CROSS_CITY_FEE = "cross_city_fee"
    '''跨城费'''

    def to_standard(self) -> ChargeCode:

        """
        转换为标准网约车订单费用代码
        """
        c = CaocaoChargeCode

        if self == c.START_FEE:
            return ChargeCode.INITIAL
        if self == c.TRAVEL_KM_FEE:
            return ChargeCode.DISTANCE
        if self == c.TRAVEL_MINUTE_FEE:
            return ChargeCode.DURATION
        if self == c.LONG_KM_FEE:
            return ChargeCode.LONG_DISTANCE
        if self == c.LONG_KM2_FEE:
            return ChargeCode.LONG_DISTANCE
        if self == c.NIGHT_FIX:
            return ChargeCode.NIGHT_INITIAL
        if self == c.NIGHT_FEE:
            return ChargeCode.NIGHT_LONG
        if self == c.LOWEST_COST_FEE:
            return ChargeCode.BASE
        if self == c.PARK_FEE:
            return ChargeCode.PARKING
        if self == c.BRIDGE_FEE or self == c.HIGHT_SPEED_FEE:
            return ChargeCode.TOLL
        if self == c.CROSS_CITY_FEE:
            return ChargeCode.CROSS_CITY
        if self == c.REFUND_FEE:
            return ChargeCode.REFUND
        if self == c.DISCOUNT_FEE:
            return ChargeCode.DISCOUNT
        return ChargeCode.OTHER
        


class CaocaoPriceDetail(BaseModel):

    amount: int
    chargeCode: CaocaoChargeCode
    chargeDesc: str

    def to_standard(self) -> PriceDetail:

        """
        转换为标准网约车订单价格明细
        """
        return PriceDetail(
            amount=self.amount,
            description=self.chargeDesc,
            code=self.chargeCode.to_standard()
        )

class CaocaoLineType(IntEnum):

    """
    曹操出行线路类型
    """

    COMMON = 0
    '''普通线路，与None, False同等'''
    FIXED = 1
    '''一口价线路'''

    def to_fare_type(self) -> RideHailingOrderFareType:

        """
        转换为标准网约车订单计费类型
        """
        if self == CaocaoLineType.FIXED:
            return RideHailingOrderFareType.ROUTE_FIXED
        return RideHailingOrderFareType.COMMON
    
    @classmethod
    def from_standard(cls, fare_type: RideHailingOrderFareType) -> 'CaocaoLineType':

        """
        从标准网约车订单计费类型转换
        """
        if fare_type in (RideHailingOrderFareType.ROUTE_FIXED, RideHailingOrderFareType.SPECIAL_FIXED):
            return cls.FIXED
        return cls.COMMON
    
    def __bool__(self):
        return self != self.COMMON


class CaocaoOrderTag(IntEnum):

    """
    曹操出行订单价格标签
    """
    FIXED = 1
    '''一口价'''
    PREPAY_CASH = 2
    '''前置现金支付'''
    NORMAL = 3
    '''正常计费'''
    CASH = 4
    '''现金支付'''

    @classmethod
    def from_standard(cls, fare_type: RideHailingOrderFareType) -> 'CaocaoOrderTag':

        """
        从标准网约车订单计费类型转换
        """
        if fare_type in (RideHailingOrderFareType.ROUTE_FIXED, RideHailingOrderFareType.SPECIAL_FIXED):
            return cls.FIXED
        return cls.NORMAL
    
    def __bool__(self):
        return self != self.NORMAL
