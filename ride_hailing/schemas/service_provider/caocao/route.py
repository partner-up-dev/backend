"""
author: Lan_zhijiang
date: 2024-10-31
desc: 曹操出行路线相关数据模型
issues: 
    #2
references: 

"""

# typing
from typing import List, Optional
from enum import IntEnum
from pydantic import BaseModel, Field
import time

# typing - business module
from app.schemas.base.route import DrivenRouteItem, TrafficStatus, DrivenRouteItemType, NavigationInfo


'''routeInfo'''
class CaocaoLinkType(IntEnum):
    COMMON = 0
    SHIPPING_LANE = 1
    TUNNEL = 2
    BRIDGE = 3
    TRESTLE = 4

    def to_standard(self) -> DrivenRouteItemType:

        """
        转换为标准路段类型
        """
        c = CaocaoLinkType

        if self == c.SHIPPING_LANE:
            return DrivenRouteItemType.SHIPPING_LANE
        elif self == c.TUNNEL:
            return DrivenRouteItemType.TUNNEL
        elif self == c.BRIDGE:
            return DrivenRouteItemType.BRIDGE
        elif self == c.TRESTLE:
            return DrivenRouteItemType.TRESTLE
        return DrivenRouteItemType.COMMON

class CaocaoTrafficStatus(IntEnum):
    UNKNOWN = 0
    SMOOTH = 1
    SLOW = 2
    JAM = 3
    GRIDLOCK = 4

    def to_standard(self) -> TrafficStatus:

        """
        转换为标准交通状态
        """
        if self == CaocaoTrafficStatus.SMOOTH:
            return TrafficStatus.SMOOTH
        elif self == CaocaoTrafficStatus.SLOW:
            return TrafficStatus.SLOW
        elif self == CaocaoTrafficStatus.JAM:
            return TrafficStatus.JAM
        elif self == CaocaoTrafficStatus.GRIDLOCK:
            return TrafficStatus.GRIDLOCK
        return TrafficStatus.UNKNOWN

class CaocaoStepLink(BaseModel):

    length: int = 0
    time: int = 0
    linkType: CaocaoLinkType = CaocaoLinkType.COMMON
    trafficStatus: CaocaoTrafficStatus = CaocaoTrafficStatus.UNKNOWN
    coords: str = ""
    """lat,lng;lat,lng..."""
    roadName: str = ""

    def to_standard(self) -> DrivenRouteItem:

        """
        转换为标准路段信息
        """
        return DrivenRouteItem(
            length=self.length,
            duration=self.time,
            type=self.linkType.to_standard(),
            traffic_status=self.trafficStatus.to_standard(),
            coords=self.coords,
            nickname=self.roadName
        )

class CaocaoStep(BaseModel):

    length: int = 0
    '''米'''
    time: int = 0
    '''秒'''
    links: List[CaocaoStepLink]

    def to_standard(self) -> List[DrivenRouteItem]:

        """
        转换为标准路线信息
        """
        return [
            link.to_standard() for link in self.links
        ]

'''/routeInfo'''

'''navigationInfo'''
class CaocaoETAInfo(BaseModel):

    curPointIndex: int = 0
    curStepIndex: int = 0
    '''当前司机所在位置的道路索引（相对于steps）'''
    curLinkIndex: int = 0
    '''当前司机所在位置的道路索引（相对于steps[curStepIndex].links）'''
    isMatchNaviPath: int = 1
    remainDistance: int = 0
    '''米'''
    remainTime: int = 0
    '''秒'''
    remainLightCount: int = 0
    '''剩余红绿灯数''' 
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    '''毫秒时间戳'''
    lat: float = 0.0
    '''司机当前位置纬度'''
    lng: float = 0.0
    '''司机当前位置经度'''
    direction: float = 0.0
    '''司机当前方向；0-1 -> 0-360'''
    speed: float = 0.0

    def to_standard(self) -> NavigationInfo:

        """
        转换为标准导航信息
        """
        return NavigationInfo(
            speed=self.speed,
            remain_length=self.remainDistance,
            remain_duration=self.remainTime,
            remain_traffic_lights=self.remainLightCount,
            timestamp=self.timestamp / 1000,
            lat=self.lat,
            lng=self.lng,
            heading=self.direction * 360
        )

'''/navigationInfo'''
