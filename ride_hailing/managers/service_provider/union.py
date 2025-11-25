"""
author: Lan_zhijiang
date: 2024-10-22
desc: 服务提供商模块 管理器 集合
issues: 

references: 

"""

from typing import List, Dict
from app.managers.service_provider import ServiceProviderManager
from app.schemas.service_provider import ServiceProvider
from app.managers.service_provider.caocao import CaocaoManager
from app.libs.exceptions import NotFound


AVAILABLE_SERVICE_PROVIDERS: List[ServiceProviderManager] = [
    CaocaoManager
]
SERVICE_PROVIDER_MAPPER: Dict[ServiceProvider, ServiceProviderManager] = {
    ServiceProvider.CAOCAO: CaocaoManager
}

def get_service_provider_manager(service_provider_id: ServiceProvider) -> ServiceProviderManager.__class__:

    """
    根据SP_ID获取服务提供商管理器

    找不到则会抛出NotFound
    """
    try:
        return SERVICE_PROVIDER_MAPPER[
            service_provider_id if isinstance(service_provider_id, ServiceProvider) else ServiceProvider(service_provider_id)
        ]
    except KeyError:
        raise NotFound('service_provider', (('__getitem__', ('key', service_provider_id)),))
