"""
author: Lan_zhijiang
date: 2024-10-17
desc: 网约车订单 价格相关数据模型
issues: 
    #7
references: 

"""

__module_name__ = "OrderPriceSchema"

# typing
from typing import Annotated, List, Tuple
from pydantic import Field
from enum import Enum
# from app.schemas import BaseSchema, enum_serializer
from backend_common.schemas import BaseCommonSchema
from backend_common.schemas.serializers import enum_serializer
from backend_common.libs.i18n import TranslatableEnum

# i18n
from backend_common.libs import i18n
t = i18n.get_translator(__module_name__, localedir="data/locales")
de_p = i18n.pgettext_placeholder

# typing-business module
from app.schemas.order.config import RideType

# libs
import time
import datetime

# utils
# from app.utils.base import get_datetime_with_timezone
from backend_common.utils.datetime import get_datetimez


class RideHailingOrderFareType(Enum):

    """
    网约车订单计费类型

    https://app.apifox.com/link/project/5303644/apis/schema-125303510
    """
    COMMON = "common" # 普通计费
    SPECIAL_FIXED = "special_fixed" # 尊享一口价
    ROUTE_FIXED = "route_fixed" # 路线一口价

class ChargeCode(TranslatableEnum):

    """
    费用代码（类型）

    https://app.apifox.com/link/project/5303644/apis/schema-125280339
    """
    def __init__(self, *args):
        super().__init__(t, "charge_code")

    INITIAL = de_p("charge_code", "initial")
    '''起步费用'''
    BASE = de_p("charge_code", "base")
    '''基础费用'''
    DISTANCE = de_p("charge_code", "distance")
    '''里程费用'''
    DURATION = de_p("charge_code", "duration")
    '''时长费用'''
    LONG_DISTANCE = de_p("charge_code", "long_distance")
    '''远途费用'''
    NIGHT_INITIAL = de_p("charge_code", "night_initial")
    '''夜间起步费用'''
    NIGHT_LONG = de_p("charge_code", "night_long")
    '''夜间长里程费用'''
    CROSS_CITY = de_p("charge_code", "cross_city")
    '''跨城费用'''
    PARKING = de_p("charge_code", "parking")
    '''停车费用'''
    TOLL = de_p("charge_code", "toll")
    '''路桥费用'''
    OTHER = de_p("charge_code", "other")
    '''其他费用'''
    DISCOUNT = de_p("charge_code", "discount")
    REFUND = de_p("charge_code", "refund")


class PriceDetail(BaseCommonSchema):

    """
    价格明细条目
    """
    amount: int = 0  # 金额（分）
    description: str | None = None  # 描述
    code: Annotated[ChargeCode, enum_serializer]  # 费用代码

    def to_split_bill_detail(self) -> Tuple[str, int]:
            
        """
        转换为平账账单明细格式
        """
        return self.description, self.amount


class PriceInfo(BaseCommonSchema):

    """
    价格信息

    对应车型在（路线以及其它配置下的）的价格信息 \n
    注意路线与其它配置没有被存储于此，但具有必然联系（因为一个订单的路线、配置只有一个，但可以有多个车型）

    https://app.apifox.com/link/project/5303644/apis/schema-125318944
    """
    ride_type: str 
    '''车型；为RideTypeRef'''
    price_key: str
    type: Annotated[RideHailingOrderFareType | None, enum_serializer]  # 计费类型
    total: int = 0  # 原始价格
    actual: int = 0  # 实际价格
    details: List[PriceDetail] = Field(default_factory=list)  # 价格明细
    expired_at: datetime.datetime | None = None
    """价格过期时间"""

    @property
    def is_expired(self) -> bool:

        """
        是否过期
        """
        return self.expired_at < get_datetimez()
