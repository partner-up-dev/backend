"""
author: Lan_zhijiang
date: 2024-12-08
desc: RideHailing Advertisement Module Manager
issues:    
    #20
references: 

"""

# typing
import typing
from backend_common.managers import BaseManager

# logging
from app.libs.logs import top_logger as logging
logger = logging.getChild("Advertisement")

# exceptions
from app.libs.exceptions import NotFound

# db
from backend_common.libs.database import supabase_serv_db

# utils
from backend_common.utils.pydantic import get_pri_attr_value

# managers
from app.managers.advertisement_provider.union import get_advertisement_provider_manager

# schema
from app.schemas.advertisement import AdvertisementItem, AdvertisementSpot, AdvertisementLink


class AdvertisementItemManager(BaseManager):

    """
    广告项管理器
    """

    _DB_SCHEMA = "ride_hailing"
    _TABLE = "advertisement_item"

    @classmethod
    def get(cls,
        spot: AdvertisementSpot,
        source_str: str = None
    ) -> typing.List[AdvertisementItem]:

        """
        获取广告项

        :param spot: 广告位
        :param source_str: 溯源字符串

        :exception NotFound: 没有该广告位可用的广告项
        """
        logger.info("Get advertisement items in spot %s", spot)

        # 1. 从表中按照spot筛选出可用的广告项
        result: typing.List[AdvertisementItem] = []
        items = supabase_serv_db.fetch(
            table_name=get_pri_attr_value(cls._TABLE),
            schema=get_pri_attr_value(cls._DB_SCHEMA),
            filters=(
                ("overlaps", ("spots", (spot.value,))),
            ),
            logger=logger
        )

        # 2. 遍历每一个广告项，补充完整数据
        for item in items:
            item = AdvertisementItem(**item)

            # 2.1 海报
            if not item.post:
                item.post = cls.__get_post(item, spot, source_str)

            # 2.2 链接
            link = cls.__get_link(item, spot, source_str)

            item = spot.item_cls(
                **item.dump_as_dict(),
                **link.dump_as_dict()
            )

            result.append(item)

        return result

    @classmethod
    def __get_post(cls, item: AdvertisementItem, spot: AdvertisementSpot, source_str: str = None) -> str:

        """
        获取广告项的海报

        :param item: 广告项
        """
        # 1. get advertisement provider manager
        provider_manager = get_advertisement_provider_manager(item.provider)

        # 2. get poster
        return provider_manager.get_poster(item.advertiser_item_id, spot, source_str)
    
    @classmethod
    def __get_link(cls, item: AdvertisementItem, spot: AdvertisementSpot, source_str: str = None) -> AdvertisementLink:

        """
        获取广告项的链接

        :param item: 广告项
        """
        # 1. get advertisement provider manager
        provider_manager = get_advertisement_provider_manager(item.provider)

        # 2. get link
        return provider_manager.get_link(item.advertiser_item_id, spot, source_str)


