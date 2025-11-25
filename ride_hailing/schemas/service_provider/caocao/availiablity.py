"""
author: Lan_zhijiang
date: 2024-10-28
desc: 曹操出行开放平台 服务可用性相关数据模型
issues: 

references: 

"""

# typing
from pydantic import BaseModel

# typing - business module
from app.schemas.service_provider.caocao.base import OnOff
from app.schemas.service_provider.caocao.config import CaocaoCarType


class CityAvailability(BaseModel):

    """
    城市服务开通状态

    https://app.apifox.com/link/project/5283937/apis/schema-125419497
    """
    choiceness: OnOff
    '''优选车型'''
    cityCode: str
    cityName: str
    comfortable: OnOff
    '''舒适性'''
    commercial: OnOff
    '''商务车型'''
    economic_business: OnOff
    '''经济商务'''
    luxurious: OnOff
    '''豪华车型'''
    newEnergy: OnOff
    '''新能源车型'''
    taxi: OnOff
    '''出租车'''

    def is_car_type_available(self, car_type: CaocaoCarType) -> bool:

        """
        判断车型是否开通

        :param car_type: 车型
        :return: 是否开通
        """
        if car_type == CaocaoCarType.CHOICENESS:
            return self.choiceness.__bool__()
        elif car_type == CaocaoCarType.COMFORTABLE:
            return self.comfortable.__bool__()
        elif car_type == CaocaoCarType.BUSINESS:
            return self.commercial.__bool__()
        elif car_type == CaocaoCarType.ECONOMIC_BUSINESS:
            return self.economic_business.__bool__()
        elif car_type == CaocaoCarType.LUXURIOUS:
            return self.luxurious.__bool__()
        elif car_type == CaocaoCarType.NEW_ENERGY:
            return self.newEnergy.__bool__()
        # elif car_type == CaocaoCarType.TAXI:
        #     return self.taxi.__bool__()
        else:
            return False
        
    def get_all_availiable_car_types(self) -> list[CaocaoCarType]:

        """
        获取所有可用的车型

        :return: list
        """
        return [car_type for car_type in CaocaoCarType if self.is_car_type_available(car_type)]
