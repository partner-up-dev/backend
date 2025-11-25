"""
author: Lan_zhijiang
date: 2024-10-22
desc: 服务提供商模块 管理器 基本
issues: 
    #7
references: 
    https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/ServiceProvider
"""

# typing
from typing import Dict, Tuple, TypeVar, Generic, List, Any
# from app.managers import BaseManager
from backend_common.managers import BaseManager
from fastapi import Request

# typing-business module
from app.schemas.service_provider import ServiceProvider, ServiceProviderOrder
from app.schemas.order import RideHailingOrder, RideHailingOrderCancelReason, RideHailingOrderStatus, Competitor, DriverInfo
from app.schemas.order.config import RideHailingPreference, RideTypes, RideType
from app.schemas.order.price import PriceInfo, PriceDetail
if __name__ == "__main__": 
    from app.schemas.order.callback import OrderCallback
from app.schemas.base.route import Route, DrivenRoute, NavigationInfo, DriverLocation

if __name__ == "__main__":
    from app.managers.order import OrderManager

# libs
import time


OrderIdType = TypeVar("OrderIdType", str, int)
OrderStatusType = TypeVar("OrderStatusType")
class ServiceProviderManager(BaseManager[Any], Generic[OrderIdType, OrderStatusType]):

    """
    （网约车）服务提供商基类

    doc:
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/ServiceProvider
    """

    _SERVICE_PROVIDER_ID: ServiceProvider | None = None

    @property
    def driver_info(self) -> DriverInfo:

        """
        获取司机信息
        """
        raise NotImplementedError()

    @classmethod
    def get_available_ride_types(
        cls, route: Route, preference: RideHailingPreference | None = None
    ) -> RideTypes:

        """
        获取所有可用（符合要求的）的车型

        :param route: 路线信息 
        :param preference: 打车偏好

        :return: RideTypes

        默认开启加盟运力、接力单，关闭拼车

        """

    @classmethod
    def is_available(
        cls, ride_type: RideType, 
        route: Route, preference: RideHailingPreference | None = None,
        **kwargs
    ) -> bool:

        """
        查询当前车型是否可用

        :param ride_types: 被筛选的车型
        :param route: 路线
        :param preference: 打车偏好

        :return: bool
        """

    @staticmethod
    def is_route_reservable(route: Route) -> bool:

        """
        当前下单是否为预约单

        太过遥远可能会抛出ParamsInvalid异常

        :param route: 路线信息

        :return: bool
        """

    @staticmethod
    def is_price_info_valid(price_info: PriceInfo) -> bool:

        """
        价格信息是否合法

        :param price_info: 价格信息

        :return: bool
        """
        raise NotImplementedError()

    @classmethod
    def estimate_price(
        cls, 
        route: Route,
        ride_types: List[RideType],
        preference: RideHailingPreference | None = None,
        **kwargs
    ) -> List[PriceInfo]:
        
        """
        （批量）获取（预估的）车型配置的价格

        :param route: 路线信息
        :param preference: 打车偏好
        :param ride_types: 车型列表（必须传递）

        :return: List[PriceInfo]
        """
        pass

    @classmethod
    def fetch_by_id(cls, _id, *fields) -> dict:

        """
        获取服务商订单数据

        :param _id: 服务商端订单ID
        :param *fields: （不支持）需要获取的字段

        :return: 服务商订单数据
        """
        pass

    @property
    def standard_order(self) -> RideHailingOrder:

        """
        获取标准网约车订单

        :return: 标准网约车订单
        """
        return self.schema.to_standard()
        
    @classmethod
    def place_order(
        cls, route: Route, preference: RideHailingPreference,
        prices: List[PriceInfo], order_manager: 'OrderManager'
    ) -> 'ServiceProviderManager':
        
        """
        下单（打车）

        :param route: 路线信息
        :param preference: 打车偏好
        :param prices: 价格信息
        :param order_id: 外部订单ID（标准网约车订单ID）

        :return: 服务提供商管理器
        """
        pass

    @property
    def cancel_fee(
        self
    ) -> int:
        
        """
        获取取消订单的费用

        如果已经取消，则是实际的取消费用 \n
        如果还未取消，则是预估的取消费用

        :param order_id: 服务商端订单ID

        :return: int 取消费用（分） -1代表不可以取消
        """

    @classmethod
    def __cancel_order_cls(cls, order_id: OrderIdType, reason: RideHailingOrderCancelReason, detail: str | None = None) -> int:

        """
        取消订单（类方法模式）

        :param order_id: 服务商端订单ID
        :param cancel_code: 取消原因代码
        :param cancel_reason: 取消原因详情
        :param who_cancel: 取消方

        :return: int 取消费用（分）
        """

    def cancel_order(
        self, reason: RideHailingOrderCancelReason, detail: str | None = None
    ) -> int:
        
        """
        取消订单

        :param reason: 取消原因代码
        :param detail: 取消原因详情，没有则翻译取消原因代码

        :return: int 取消费用（分）
        """
        return self.__cancel_order_cls(self.id, reason, detail)
        
    @classmethod
    def __get_driven_route(
        cls, order_id: OrderIdType
    ) -> DrivenRoute | None:

        """
        获取行驶路线（类方法模式）

        :param order_id: 服务商端订单ID

        :return: DrivenRoute
        """

    @property
    def driven_route(
        self
    ) -> None | DrivenRoute:
        
        """
        获取（司机当前）行驶路线

        :return: DrivenRoute | None
        """
        return self.__get_driven_route(self.id)
    
    @classmethod
    def __get_driver_location(
        cls, order_id: OrderIdType
    ) -> DriverLocation | None:

        """
        获取司机位置（类方法模式）

        :param order_id: 服务商端订单ID

        :return: 司机位置信息
        """

    @property
    def driver_location(
        self
    ) -> DriverLocation | None:
        
        """
        获取司机位置

        :return: 司机位置信息
        """
        return self.__get_driver_location(self.id)
    
    @classmethod
    def __get_navigation_info(
        cls, order_id: OrderIdType
    ) -> NavigationInfo | None:

        """
        获取导航信息（类方法模式）

        :param order_id: 服务商端订单ID

        :return: 导航信息
        """

    @property
    def navigation_info(
        self
    ) -> NavigationInfo | None:
        
        """
        获取导航信息（司机位置+其它导航信息）

        :return: 导航信息
        """

    @classmethod
    def __confirm_fare_cls(
        cls, order_id: OrderIdType, allowance: int = 0
    ) -> bool:
        
        """
        确认费用（类方法模式）

        :param order_id: 服务商端订单ID
        :param allowance: 补贴

        :return: 是否成功
        """

    def confirm_fare(
        self, allowance: int = 0
    ) -> bool:
        
        """
        确认费用

        :param allowance: 补贴

        :return: 是否成功
        """
        self.__confirm_fare_cls(self.id, allowance)

    @classmethod
    def __review_order_cls(
        cls, order_id: OrderIdType, rating: int = 5, comment: str | None = None
    ) -> None:
        
        """
        评价订单（类方法模式）

        :param order_id: 服务商端订单ID
        :param rating: 评分 1-5
        :param comment: 评论
        """

    def review_order(
        self, 
        rating: int = 5, comment: str | None = None
    ):
        
        """
        评价订单

        :param rating: 评分 1-5
        :param comment: 评论
        """

    @property
    def fare(
        self
    ) -> Tuple[int, List[PriceDetail]]:
        
        """
        获取费用信息（总价与费用明细）
        """

    @property
    def inner_status(self) -> OrderStatusType:

        """
        获取内部订单状态
        """

    @property
    def status(
        self
    ) -> RideHailingOrderStatus:
        
        """
        获取（标准）订单状态
        """
        return self.inner_status.to_standard()

    @property
    def winner(self) -> Competitor:

        """
        获取胜出者（胜出的车型 + 服务提供商订单ID）

        对一个服务供应商呼叫多种车型，则服务供应商内部会处理其间的竞争
        """

    @classmethod
    def resolve_callback(
        cls, request: Request
    ) -> "OrderCallback":
        
        """
        解析回调（通知）

        将服务商额回调通知进行解密、校验、解析，返回标准的通知体

        :param request: FastAPI请求体

        :return: 标准回调通知
        """
        pass

    def sync_fare_type(self, order_manager: 'OrderManager'):

        """
        同步到统一订单的费用类型
        """

    def sync_status(self, order_manager: 'OrderManager'):

        """
        同步到统一订单的状态信息
        """

    def sync_timeline(self, order_manager: 'OrderManager'):

        """
        同步到统一订单的时间线信息
        """

    def sync_drive(self, order_manager: 'OrderManager'):

        """
        同步到统一订单的行驶信息
        """

    def sync(self, order_manager: 'OrderManager'):

        """
        同步服务供应商的信息到统一订单
        """
        self.sync_status(order_manager)
        self.sync_timeline(order_manager)
        self.sync_drive(order_manager)
        self.sync_fare_type(order_manager)

