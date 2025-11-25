"""
author: Lan_zhijiang
date: 2024-12-08
desc: 网约车广告主要数据模型
issues: 
    #20
references: 

"""

from typing import Optional
from enum import Enum
from pydantic import Field
from backend_common.schemas import BaseCommonSchema, BaseSchema

class AdvertisementProvider(Enum):

    """
    广告商
    """
    DIDI_UNION = "didi_union"
    '''滴滴联盟'''

class AdvertisementSpot(Enum):

    """
    广告位
    """
    WECHAT_MP_ORDER_PLACING = "wechat_mp_order_placing"
    '''微信小程序下单页'''

    @property
    def link_cls(self):

        """
        获取广告位对应的"链接"数据模型
        """
        if self == AdvertisementSpot.WECHAT_MP_ORDER_PLACING:
            return MPAdvertisementLink
        
    @property
    def item_cls(self):

        """
        获取广告位对应的"广告项"数据模型
        """
        if self == AdvertisementSpot.WECHAT_MP_ORDER_PLACING:
            return WechatMPAdvertisementItem
        
    @property
    def is_mp(self):

        """
        是否为小程序广告位
        """
        return self in (AdvertisementSpot.WECHAT_MP_ORDER_PLACING,)
    
    @property
    def is_wechat_mp(self):

        """
        是否为微信小程序广告位
        """
        return self in (AdvertisementSpot.WECHAT_MP_ORDER_PLACING,)


AdvertisementItemRef = int
AdvertiserSideItemId = str
class AdvertisementItem(BaseSchema[AdvertisementItemRef]):

    """
    基本广告项
    """
    advertiser_item_id: AdvertiserSideItemId
    '''广告商侧广告项ID'''
    provider: AdvertisementProvider
    spots: list[AdvertisementSpot] = Field(default_factory=list)
    title: str
    desc: str
    cover: Optional[str] = None
    '''横幅链接；公共可访问'''
    post: Optional[str] = None
    '''海报链接；公共可访问'''

class AdvertisementLink(BaseCommonSchema):

    """
    广告链接
    """
    pass

class MPAdvertisementLink(AdvertisementLink):

    """
    小程序广告链接
    """
    appid: str
    '''小程序appid'''
    path: str
    '''小程序路径'''

class MPAdvertisementItem(AdvertisementItem, MPAdvertisementLink):

    """
    小程序广告项
    """
    pass

class WechatMPAdvertisementItem(MPAdvertisementItem):

    """
    微信小程序广告项（末端广告项）

    在 微信小程序 客户端上展示的广告项
    """
    pass

class AliMPAdvertisementItem(MPAdvertisementItem):

    """
    支付宝小程序广告项（末端广告项）

    在 支付宝小程序 客户端上展示的广告项
    """
    pass

