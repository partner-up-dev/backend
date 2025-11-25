"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 配置类数据模型
issues: 
    #2
references: 

"""

__module_name__ = "CaocaoConfigSchema"

# typing
from enum import IntEnum

# typing - business module
from app.schemas.order.config import CarType

# libs
from backend_common.libs.i18n import pgettext_placeholder as de_p, get_translator
t = get_translator(__module_name__, localedir="data/locales")

class CaocaoCarType(CarType):

    """
    曹操出行车型代码

    https://app.apifox.com/link/project/5283937/apis/schema-125443488
    """

    def __init__(self, *args, context = "car_type", domain = __module_name__):
        super().__init__(t, context, domain)

    NEW_ENERGY = de_p("car_type", "2", int)
    '''新能源'''
    COMFORTABLE = de_p("car_type", "3", int)
    '''舒适型'''
    LUXURIOUS = de_p("car_type", "4", int)
    '''豪华型'''
    BUSINESS = de_p("car_type", "5", int)
    '''商务型'''
    ECONOMIC_BUSINESS = de_p("car_type", "6", int)
    '''经济商务'''
    CHOICENESS = de_p("car_type", "7", int)
    '''优选型'''
    SMART = de_p("car_type", "14", int)
    '''智能大白车'''
    LIMO = de_p("car_type", "15", int)
    '''礼帽专车'''

    @classmethod
    def from_str_or_int(cls, value):
        if isinstance(value, str):
            return cls(int(value))
        elif isinstance(value, int):
            return cls(value)
        else:
            raise ValueError(f"Invalid value type: {type(value)}")

class CaocaoSMSPolicy(IntEnum):

    BOTH = 1
    '''叫车人和乘车人都发送'''
    PASSENGER = 2
    '''只发给乘车人'''
    CALLER = 3
    '''只发给叫车人'''
    NONE = 4
    '''都不发送'''
