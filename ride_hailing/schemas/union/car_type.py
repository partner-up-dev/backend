"""
author: Lan_zhijiang
date: 2024-11-02
desc: 网约车配置中的车型的集合，将各服务提供商的车型汇集于此并提供映射
issues: 
    #5
references: 

"""

# typing
from typing import Dict

# typing - business module
from app.schemas.order.config import CarType, ServiceProvider
from app.schemas.service_provider.caocao.config import CaocaoCarType

# libs
from app.libs.exceptions import NotFound


CAR_TYPE_MAPPER: Dict[ServiceProvider, CarType] = {
    ServiceProvider.CAOCAO: CaocaoCarType
}

def get_car_type(service_provider_id: ServiceProvider) -> CarType.__class__:

    """
    获取指定服务提供商的车型映射
    """
    try:
        return CAR_TYPE_MAPPER[
            service_provider_id if isinstance(service_provider_id, ServiceProvider) else ServiceProvider(service_provider_id)
        ]
    except KeyError:
        raise NotFound('car_type', (('__getitem__', ('key', service_provider_id)),))

