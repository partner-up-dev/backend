"""
author: Lan_zhijiang
date: 2024-10-24
desc: 订单模块 回调通知 相关数据模型
issues: 
    #7
references: 

"""

# typing
from typing import Generic, Type, TypeVar, Union
from pydantic import field_validator
# from app.schemas import BaseSchema
from backend_common.schemas import BaseCommonSchema
from enum import Enum

# typing - business module
from app.managers.service_provider import ServiceProviderManager
from app.schemas.order import RideHailingOrderStatus
from interface_main.schemas.partner_request.split_the_bill import SplitBillStatus
from app.schemas.service_provider import ServiceProvider as ServiceProviderID

# libs
import datetime
from backend_common.utils.datetime import get_datetimez


class OrderCallbackType(Enum):

    """
    回调通知类型
    """
    UNKNOWN = "unknown"
    '''未知类型'''
    ORDER_STATUS_UDPATE = "order_status_update"
    '''网约车订单状态更新'''
    SP_ORDER_STATUS_UPDATE = "sp_order_status_update"
    '''服务提供商订单状态更新'''
    SPLIT_BILL_STATUS_UPDATE = "split_bill_status_update"
    '''平账账单状态更新'''

class OrderStatusUpdateContent(BaseCommonSchema):

    """
    网约车订单状态更新回调内容
    """
    new_status: RideHailingOrderStatus
    '''新状态'''


class SPOrderStatusUpdateContent(BaseCommonSchema):

    """
    服务提供商订单状态更新回调内容
    """
    order_id: int
    '''订单ID'''
    service_provider_order_id: str
    '''服务提供商的订单ID'''
    service_provider_id: ServiceProviderID
    '''服务提供商'''
    new_status: RideHailingOrderStatus
    '''新状态（标准状态）'''
    instance: ServiceProviderManager  # TODO 导入会重复循环；不导入又不行
    """
    服务提供商实例
    """

class SplitBillStatusUpdateContent(BaseCommonSchema):

    """
    平账账单状态更新回调内容
    """
    new_status: SplitBillStatus


# T = TypeVar("ContentType", bound=OrderCallbackType)
class OrderCallback(BaseCommonSchema):

    """
    标准订单回调通知

    所有需要通知订单的回调，都遵循这一数据模型
    """

    timestamp: datetime.datetime = get_datetimez()
    '''毫秒时间戳'''
    type: OrderCallbackType
    '''回调通知类型'''
    content: Union[
        SPOrderStatusUpdateContent,
        SplitBillStatusUpdateContent,
        None
    ]

