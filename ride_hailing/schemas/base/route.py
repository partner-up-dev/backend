"""
author: Lan_zhijiang
date: 2024/06/07
desc: Route and Location Schema, the sub schema of Ride Hailing Partner Request
issues:
    #21 http://git.hadream.ltd/anana/backend/main/-/work_items/21#note_2153
references:
    https://app.apifox.com/link/project/4406548/apis/schema-99342080
    https://app.apifox.com/link/project/4406548/apis/schema-94880350
"""

# typing
import time
import typing
# from app.schemas import BaseSchema, BaseRootSchema
from backend_common.schemas import BaseSchema, BaseRootSchema, BaseCommonSchema
from typing import Union, List, Tuple
from enum import Enum
from pydantic import Field

# util
from app.utils.encryption import Encryption


class Location(BaseSchema):

    _ID_TYPE = "hash"

    friendly_address: str  # max 12
    address: List[str]
    lat: float
    lng: float


class RouteItem(BaseCommonSchema):

    datetime: Tuple[float | None, int | None]  
    '''
        timestamp(以秒为单位的时间戳，但是允许用小数表示更小单位) 
        timeloss_tolerance(min) 
    '''
    location: str  # location _id


class Route(BaseRootSchema):

    root: List[RouteItem] = Field(default_factory=list, min=2, max=10)

    # TODO 确保RouteItem的datetime是递增的
    # TODO 确保Route[0]的datetime是当前时间之后的
    # TODO 确保Route[0]的datetime有值

''' DrivenRouteInfo '''
class DrivenRouteItemType(Enum):
    COMMON = "common"
    '''普通道路'''
    SHIPPING_LANE = "shipping_lane"
    '''航道'''
    TUNNEL = "tunnel"
    '''隧道'''
    BRIDGE = "bridge"
    '''桥梁'''
    TRESTLE = "trestle"
    '''高架桥'''
    EXPRESSWAY = "expressway"
    '''高速公路'''

class TrafficStatus(Enum):
    UNKNOWN = "unknown"
    '''未知'''
    SMOOTH = "smooth"
    '''畅通'''
    SLOW = "slow"
    '''缓行'''
    JAM = "jam"
    '''拥堵'''
    GRIDLOCK = "gridlock"
    '''严重拥堵'''
    BLOCKED = "blocked"
    '''封闭'''

class DrivenRouteItem(BaseCommonSchema):

    """
    路线段

    https://app.apifox.com/link/project/5303644/apis/schema-126306205
    """

    length: int = 0
    '''分段长度；单位米'''
    duration: int = 0
    '''分段预计耗时；单位秒'''
    type: DrivenRouteItemType
    '''分段类型'''
    traffic_status: TrafficStatus
    '''分段交通状态'''
    coords: str
    '''分段坐标；格式："lat,lng;lat,lng;lat,lng..."'''
    nickname: str | None = None
    '''道路名称'''


class DrivenRoute(BaseRootSchema):

    """
    行驶路线

    https://app.apifox.com/link/project/5303644/apis/schema-126306122
    """
    root: List[DrivenRouteItem] = Field(default_factory=list)

''' /DrivenRouteInfo '''

''' NavigationInfo '''
class DriverLocation(BaseCommonSchema):

    heading: float = 0
    '''车头朝向；以北为0度，顺时针旋转'''
    lat: float 
    lng: float

class NavigationInfo(DriverLocation):

    """
    导航信息
    
    https://app.apifox.com/link/project/5303644/apis/schema-126306217
    """
    heading: float = 0.0
    '''车头朝向；以北为0度，顺时针旋转；0-360'''
    speed: float = 0.0
    '''速度；km/h'''
    remain_length: int = 0
    '''剩余长度；米'''
    remain_duration: int = 0
    '''剩余时间；秒'''
    remain_traffic_lights: int = 0
    '''剩余红绿灯数'''
    timestamp: float = Field(default_factory=time.time)
    '''时间戳'''


''' /NavigationInfo '''