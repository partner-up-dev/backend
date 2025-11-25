"""
author: Lan_zhijiang
date: 2024-12-08
desc: 网约车广告模块-广告提供商基础管理器
issues: 
    #20
references: 

"""

import typing
from backend_common.managers import BaseManager

# schemas
from app.schemas.advertisement import (
    AdvertisementProvider, AdvertisementLink, AdvertiserSideItemId,
    AdvertisementSpot
)

# db
from backend_common.libs.database import supabase_serv_db

# utils
from backend_common.utils.pydantic import get_pri_attr_value


class AdvertisementProviderManager(BaseManager[typing.Any]):

    _PROVIDER_ID: AdvertisementProvider = None

    @classmethod
    def get_promotion_id(cls, spot: AdvertisementSpot) -> str:

        """
        从标准广告位ID获取广告提供商的广告位ID

        :param spot: 标准广告位ID

        :return 广告提供商的广告位ID

        TODO AdvertisementSpotManager
        """
        # 1. get advertisement spot data
        res = supabase_serv_db.fetch(
            table_name="advertisement_spot", schema="ride_hailing",
            columns=("_id",),
            filters=(
                ("eq", ("spot", spot.value)),
                ("eq", ("provider", get_pri_attr_value(cls._PROVIDER_ID).value))
            ),
        )

        return res[0]["_id"]

    @classmethod
    def get_link(cls, 
        _id: AdvertiserSideItemId,
        spot: AdvertisementSpot,
        source_str: str = None
    ) -> AdvertisementLink:

        """
        获取短链

        :param _id: 广告项id
        :param spot: 广告位
        :param source_str: 溯源字符串
        """
        pass

    @classmethod
    def get_poster(cls, 
        _id: AdvertiserSideItemId,
        spot: AdvertisementSpot,
        source_str: str = None
    ) -> str:

        """
        获取海报（链接）

        :param _id: 广告项id
        :param spot: 广告位
        :param source_str: 溯源字符串
        """
        pass
