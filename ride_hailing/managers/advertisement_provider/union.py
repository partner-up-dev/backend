"""
author: Lan_zhijiang
date: 2024-12-08
desc: 广告商管理器集合
issues: 
    #20
references: 

"""

from typing import List, Dict
from app.managers.advertisement_provider import AdvertisementProviderManager
from app.schemas.advertisement import AdvertisementProvider
from app.managers.advertisement_provider.didi_union import DidiUnionManager
from app.libs.exceptions import NotFound


AVAILABLE_PROVIDERS: List[AdvertisementProviderManager] = [
    DidiUnionManager
]
PROVIDER_MAPPER: Dict[AdvertisementProvider, AdvertisementProviderManager] = {
    AdvertisementProvider.DIDI_UNION: DidiUnionManager
}

def get_advertisement_provider_manager(provider_id: AdvertisementProvider) -> AdvertisementProviderManager.__class__:

    """
    根据广告提供商ID获取广告提供商管理器

    找不到则会抛出NotFound
    """
    try:
        return PROVIDER_MAPPER[
            provider_id if isinstance(provider_id, AdvertisementProvider) else AdvertisementProvider(provider_id)
        ]
    except KeyError:
        raise NotFound('advertisement_provider', (('__getitem__', ('key', provider_id)),))
