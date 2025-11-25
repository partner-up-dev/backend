"""
author: Lan_zhijiang
date: 2024-12-08
desc: 网约车广告模块-广告提供商：滴滴联盟的管理器
issues: 
    #20
references: 

"""

import typing
from backend_common.utils.pydantic import get_pri_attr_value

# logging
from backend_common.libs.logs import top_logger as logging
logger = logging.getChild("DidiUnionManager")

# managers
from app.managers.advertisement_provider import AdvertisementProviderManager

# schemas
from app.schemas.advertisement import AdvertisementProvider, AdvertisementSpot
from app.schemas.advertisement import (
    MPAdvertisementLink
)

# libs
from dunion.client import UnionClient
from backend_common.libs.exceptions import ParamsInvalid

# settings
from data.settings.models.dunion import get_setting


class DidiUnionManager(AdvertisementProviderManager):

    """
    滴滴联盟管理器（广告提供商）
    """
    _PROVIDER_ID = AdvertisementProvider.DIDI_UNION

    _CLIENT: UnionClient = UnionClient(
        app_key=get_setting().app_key,
        access_key=get_setting().access_key,
        log_file=get_setting().log_file,
    )   

    @classmethod
    def get_link(cls, _id, spot, source_str):

        logger.info("Generate link for activity %s in spot %s", _id, spot)

        client = get_pri_attr_value(cls._CLIENT)

        if spot.is_mp:
            link_response = client.generate_mini_link(
                activity_id=int(_id),
                promotion_id=int(cls.get_promotion_id(spot)),
                source_id=source_str or "0"
            )
            return MPAdvertisementLink(appid=link_response.data.app_id, path=link_response.data.link)
        else:
            raise ParamsInvalid("advertisement spot", spot, "not supported")

    @classmethod
    def get_poster(cls, _id, spot, source_str) -> str:

        logger.info("Generate poster for activity %s in spot %s", _id, spot)

        poster_response = get_pri_attr_value(cls._CLIENT).generate_poster_directly(
            activity_id=int(_id),
            promotion_id=int(cls.get_promotion_id(spot)),
            source_id=source_str or "0"
            # TODO: poster_type
        )

        return poster_response.data.poster_link
