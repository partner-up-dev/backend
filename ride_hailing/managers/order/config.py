"""
author: Lan_zhijiang
date: 2024-10-26
desc: 网约车订单模块 配置类 管理器
issues: 
    #7
references: 

"""

# typing
import typing
# from app.managers import BaseManager
from backend_common.managers import BaseManager

# typing - business module
from app.schemas.order.config import RideType, RideTypeForDisplay
from app.schemas.union.car_type import get_car_type

# libs
from backend_common.libs.i18n import LanguageEnum


class RideTypeManager(BaseManager, RideType):

    """
    车型管理器
    """

    _DB_SCHEMA = "ride_hailing"
    _TABLE = "ride_type"
    _IS_HASH = True
    _ID_TYPE = "hash"

    def for_display(self, lang: LanguageEnum) -> RideTypeForDisplay:

        """
        转换为用于展示的车型数据
        """
        return RideTypeForDisplay(
            _id=self._id,
            service_provider=self.service_provider.translate(lang),
            car_type=get_car_type(self.service_provider)(self.car_type).translate(lang)
        )
