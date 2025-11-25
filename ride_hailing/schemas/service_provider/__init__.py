"""
author: Lan_zhijiang
date: 2024-10-22
desc: 服务提供商模块 数据类型 基本
issues: 
    #7
references: 

"""

__module_name__ = "ServiceProviderSchema"

# typing
from typing import Generic, TypeVar
# from app.schemas import TranslatableEnum
from backend_common.libs.i18n import TranslatableEnum
from backend_common.schemas import BaseSchema

# typing - business module
if __name__ == "__main__":
    from app.schemas.order import RideHailingOrder, RideHailingOrderStatus

# i18n
from backend_common.libs import i18n
t = i18n.get_translator(__module_name__, localedir="data/locales")
_ = i18n.gettext_placeholder


class ServiceProvider(TranslatableEnum):

    """
    网约车服务提供商
    """
    def __init__(self, *args):
        super().__init__(t, None, domain=__module_name__)

    DIDI = _("didi")
    '''滴滴出行'''
    SHENZHOU = _("shenzhou")
    '''神州专车'''
    CAOCAO = _("caocao") 
    '''曹操出行'''


ServiceProviderOrderIdType = TypeVar("ServiceProviderOrderIdType")
class ServiceProviderOrder(BaseSchema[ServiceProviderOrderIdType], Generic[ServiceProviderOrderIdType]):

    """
    网约车服务提供商订单
    """

    def to_standard(self) -> 'RideHailingOrder':
        
        """
        转换为标准网约车订单
        """

class ServiceProviderOrderStatus:
    
    def to_standard(self) -> 'RideHailingOrderStatus':

        """
        转换为标准网约车订单状态
        """
