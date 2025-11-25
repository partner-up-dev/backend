# desc: 网约车服务提供商滴滴出行的相关数据模型
# references:
#   https://open.es.xiaojukeji.com/doc/openapi/introduction/orderStatus.html

from enum import Enum


class DidiRideRule(Enum):
    ''' 计价类型 '''
    FAST = 301
    TAILORED = 201  
    TAILORED_PICK_UP = 203  # 专车接机
    TAILORED_DROP_OFF = 204  # 专车送机
    LUXURY = 501
    LUXURY_PICK_UP = 503  # 豪华车接机
    LUXURY_DROP_OFF = 504  # 豪华车送机

class DidiRequireLevel(Enum):
    ''' 用车类型 '''
    FAST_NORMAL = 600  # 普通快车
    FAST_ENJOY = 900  # 快车优享
    TAILORED_NORMAL = 100  # 专车舒适
    LUXURY_NORMAL = 1000  # 普通豪华

class DidiOrderStatus(Enum):
    ''' 订单状态 '''
    ANSWERED = 300
    TIMEOUT = 311
    WAITING_FOR_PICKING_UP = 400
    DRIVIDER_ARRIVED = 410
    IN_PROGRESS = 500
    JOURNEY_END = 600
    EXCEPTION = 610
    PAID = 700

