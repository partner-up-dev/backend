"""
author: Lan_zhijiang
date: 2024-10-22
desc: 网约车订单模块 管理器 基本
issues: 
    #7
references: 
    https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order
"""

__module_name__ = "OrderManager"

# typing
from typing import Callable, Dict, List, Literal, Tuple, overload
from backend_common.managers import BaseManager

# typing-business module
from app.schemas.order import (
    RideHailingOrder, RideHailingOrderCancelReason,
    RideHailingOrderType, RideHailingOrderStatus,
    PlatformCancelReason, PassengerCancelReason,
    Competitor, DriverInfo
)
from app.schemas.order.config import (
    RideHailingPreference, Purpose as RideHailingPurpose
)
from app.schemas.order.price import PriceInfo, RideType
from app.schemas.order.callback import (
    OrderCallback, OrderCallbackType,
)
from interface_main.schemas.partner_request.split_the_bill import SplitBillStatus
from app.schemas.base.route import Route, DrivenRoute, NavigationInfo

# managers
from app.managers.service_provider.union import (
    AVAILABLE_SERVICE_PROVIDERS, get_service_provider_manager, ServiceProvider as ServiceProviderID,
    ServiceProviderManager
)
from app.managers.order.config import RideTypeManager

# db
from supabase import Client as SupabaseClient
from backend_common.libs.supabase import supabase_serv
from backend_common.utils.manager import get_supabase_db

# libs
from app.libs.exceptions import NotFound, ParamsInvalid, Forbidden, DuplicateOrConflict, PriceInfoExpired

# apis
from interface_common.authenticate import SupabaseIdentityProvider
from interface_main.apis.split_the_bill import (
    v1_split_bill_create, V1SplitBillCreateRequestBody, SplitBillType,
    v1_split_bill_prepay_paid, V1SplitBillPrepayPaidRequestBody,
    v1_split_bill_is_status
)
from interface_main.schemas.partner_request.split_the_bill.edit import (
    DistributionItemEditableContent, DistributionItemType
)
from interface_main.apis.message.approval import (
    v1_chat_approve_approval
)
from interface_main.apis.account import (
    v1_account_get_phone
)

# i18n
from backend_common.libs import i18n
t = i18n.get_translator(__module_name__, localedir="data/locales")
_ = t.gettext

# utils
from backend_common.utils.datetime import get_datetimez
import time
from app.utils.const import ASSISTANT_ACCOUNT
from app.utils.auth import get_assistant_identity_provider
from backend_common.utils.manager import get_http_api_url
from backend_common.utils.pydantic import get_pri_attr_value

# logger
from backend_common.libs.logs import top_logger as logging
logger = logging.getChild(__module_name__)

# Celery
from .tasks import send_status_callback_to_pr, cancel_split_bill

class OrderManager(BaseManager[int], RideHailingOrder):

    _DB_SCHEMA = "ride_hailing"
    _TABLE = 'order'

    def model_post_init(self, __context):
        
        super().model_post_init(__context)

    @property
    def caller(self) -> str:

        """
        获取订单的发起者
        """
        return self.passengers[0]
    
    def is_passenger(self, account_id: str) -> bool:

        """
        判断用户是否是订单的乘客
        """
        return account_id in self.passengers

    @property
    def ride_type_ins(self) -> RideTypeManager:
        """
        根据schema.ride_type从数据库获取RideTypeInstance
        """
        return RideTypeManager(self.ride_type)

    @property
    def service_provider_id(self) -> ServiceProviderID:
        """
        获取服务商ID
        """
        return self.ride_type_ins.service_provider

    @property
    def service_provider_class(self) -> ServiceProviderManager.__class__:
        """
        获取服务供应商类
        """
        return get_service_provider_manager(self.service_provider_id)
    
    @property
    def service_provider_instance(self) -> ServiceProviderManager:
        """
        获取服务供应商实例
        """
        return self.service_provider_class(self.service_provider_order_id)
    
    @property
    def driver_info(self) -> DriverInfo:

        """
        司机信息
        """
        return self.service_provider_instance.driver_info

    def must_be_passengers(self, account_id: str):
        """
        判断用户是否是订单的乘客

        不是则抛出Forbidden异常
        """
        if account_id not in self.passengers:
            raise Forbidden("You are not the creator of this order")

    @overload
    @staticmethod
    def group_ride_types_by_service_provider(
        ride_types: List[str],
    ) -> Dict[ServiceProviderID, List[str]]:
        ...

    @overload
    @staticmethod
    def group_ride_types_by_service_provider(
        ride_types: List[RideType],
    ) -> Dict[ServiceProviderID, List[RideType]]:
        ...

    @staticmethod
    def group_ride_types_by_service_provider(
        ride_types: list,
    ) -> Dict[ServiceProviderID, list]:

        """
        将车型按照服务商分组

        :param ride_types: 车型列表，可以提供ID或者RideType

        :return: Dict[ServiceProviderID, List[RideType]]
        """
        result = {}
        for item in ride_types:
            if isinstance(item, str):
                ride_type = RideTypeManager(item)
            elif isinstance(item, RideType):
                ride_type = item
            else:
                logger.warning("Invalid ride_type %s", item)
                continue

            if ride_type.service_provider not in result:
                result[ride_type.service_provider] = []
            result[ride_type.service_provider].append(ride_type)
        
        return result
    
    @staticmethod
    def group_price_info_by_service_provider(
        prices: List[PriceInfo]
    ) -> Dict[ServiceProviderID, List[PriceInfo]]:

        """
        将价格信息按照服务商分组

        :param prices: 价格信息列表

        :return: Dict[ServiceProviderID, List[PriceInfo]]
        """
        result = {}
        for price in prices:
            # get ride_type
            ride_type = RideTypeManager(price.ride_type)
            if ride_type.service_provider not in result:
                result[ride_type.service_provider] = []
            result[ride_type.service_provider].append(price)
        
        return result

    @classmethod
    def estimate_price(
        cls, 
        route: Route, 
        preference: RideHailingPreference | None = None,
        ride_types: List[str] | None = None,
        passenger_num: int = 2
    ) -> List[PriceInfo]:

        """
        获取所有可用（符合要求的）的车型以及对应的预估价格

        :param route: 路线信息
        :param preference: 打车偏好
        :param ride_types: 车型偏好 必须是ID列表，以防止捏造不存在的车型

        :return: List[PriceInfo]

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/EstimatePrice
        """
        logger.info("Estimate price of route %s", route)

        # 1. 得到需要查询的车型
        to_query_ride_types: List[RideType] = []
        # 1.1 处理ride_types，如果传递了ride_types，则直接使用，否则获取所有可用车型
        if ride_types:
            to_query_ride_types = ride_types
        else:
            # None or []
            # 1.2 遍历AVAILABLE_SERVICE_PROVIDERS，获取所有可用车型
            for provider in AVAILABLE_SERVICE_PROVIDERS:
                to_query_ride_types.extend(provider.get_available_ride_types(route, preference))
        
        # 2. 遍历查询各个车型的价格信息
        result: List[PriceInfo] = []
        # 2.1 按照服务商分组
        query_batch = cls.group_ride_types_by_service_provider(to_query_ride_types)

        # 2.2 遍历查询
        for provider_id, _ride_types in query_batch.items():
            try:
                provider = get_service_provider_manager(provider_id)
            except NotFound:
                continue
            else:
                result.extend(provider.estimate_price(
                    route=route, preference=preference, ride_types=_ride_types,
                    passenger_num=passenger_num
                ))

        return result

    @classmethod
    def what_type(cls, route: Route, preference: RideHailingPreference | None) -> RideHailingOrderType:

        """
        根据路线与配置信息判断订单类型
        
        """
        # 1. 基于配置
        if preference:
            # 1.1 如果purpose为airport_pickup或airport_dropoff，则对应转换
            # TODO 接送机单的下单时间没有限制吗？
            if preference.purpose == RideHailingPurpose.AIRPORT_PICKUP:
                return RideHailingOrderType.AIRPORT_PICKUP
            if preference.purpose == RideHailingPurpose.AIRPORT_DROPOFF:
                return RideHailingOrderType.AIRPORT_DROPOFF
            # 1.2 如果purpose为self_drive，则为租车
            if preference.purpose == RideHailingPurpose.SELF_DRIVE:
                return RideHailingOrderType.RENTAL

        # 2. 基于路线
        # 2.1 不可以早于现在
        departure_time = route.root[0].datetime[0] / 1000 # TODO 后续改为datetime类型
        if departure_time < time.time():
            raise ParamsInvalid("departure time", f"{departure_time}", "must be after now")
        # 2.1 如果 route[0] 距离现在时间小于30分钟，则为即时单
        time_delta = abs(departure_time - time.time())
        if time_delta < 30*60:
            return RideHailingOrderType.INSTANT
        # 2.2 如果 route[0] 距离现在时间大于30分钟且小于72小时，则为预约单
        if time_delta < 72*60*60:
            return RideHailingOrderType.SCHEDULED
        
        # 都不匹配则发生错误
        raise ParamsInvalid("route and config", f"{route}, {preference}")

    @classmethod
    def create(
        cls, route: Route, 
        prices: List[PriceInfo],
        passengers: List[str],
        preference: RideHailingPreference | None = None,
        partner_request: int | None = None,
        supabase: SupabaseClient = supabase_serv,
    ) -> 'OrderManager':

        """
        创建草稿订单

        :param route: 路线信息
        :param passengers: 乘客列表（UUID列表）
        :param preference: 打车偏好
        :param prices: 价格信息
        :param partner_request: 绑定的搭子请求ID
        :param supabase: 指定Supabase实例，一般是请求者的Supabase实例

        :return: RideHailingOrderManager, bool（是否需要支付（授权自动扣款或需要预付））

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Place
        """
        logger.info("Create order with route %s, passengers %s, config %s, ride_types %s, partner_request %s", route, passengers, preference, prices, partner_request)

        # 0. 校验数据
        # 0.1 手机号（只要呼叫者要配置有）
        try:
            v1_account_get_phone(
                account_id=passengers[0],
                identity_provider=get_assistant_identity_provider()
            )
        except NotFound:
            raise ParamsInvalid("caller phone", None, 'required', logger=logger)

        # 1. 创建RideHailingOrder
        # 1.1 判断type
        _type = cls.what_type(route, preference)
        # 1.2 构建competitors，根据ride_types
        competitors = [
            Competitor(**price.dump_as_dict())
            for price in prices
        ]
        grouped_competitors = cls.group_price_info_by_service_provider(competitors)
        # 1.3 创建
        order = RideHailingOrder(
            type=_type, passengers=passengers, route=route,
            competitors=grouped_competitors, preference=preference,
            timeline={"order": get_datetimez()}
        )

        # 2. 如果传递了partner_request，则关联
        order.partner_request = partner_request

        # 3. 创建到数据库
        to_insert = order.dump_for_insert()
        supabase_db = get_supabase_db(supabase=supabase)
        insert_result = supabase_db.insert(table_name=cls._TABLE, to_insert=to_insert, logger=logger, schema=cls._DB_SCHEMA)
        order = RideHailingOrder(**insert_result)

        # 4. 创建对应的平账账单
        # 4.1 创建平账账单
        try:
            min_price = min(prices, key=lambda item: item.actual)
            max_price = max(prices, key=lambda item: item.actual)
            earliest_price = min(prices, key=lambda item: item.expired_at)

            # TODO update the function
            user_identity_provider = SupabaseIdentityProvider()
            user_identity_provider.client = supabase  # RELEASE
            # user_identity_provider = get_assistant_identity_provider()  # TEST
            split_bill_create_res = v1_split_bill_create(
                type=SplitBillType.PREPAY,
                body=V1SplitBillCreateRequestBody(
                    title=_('Ride Hailing fare'), 
                    description=_("RideHailingOrder-{order_id}'s bill. You can check order's fare and distribute the bill here. Once this bill contributed, order will be placed automatically.").format(
                        order_id=order.id
                    ),
                    actual_range=(min_price.actual, max_price.actual),
                    payer=ASSISTANT_ACCOUNT,
                    details=[detail.to_split_bill_detail() for detail in max_price.details],
                    distribution={
                        passenger: DistributionItemEditableContent(
                            type=DistributionItemType.RELATIVE,
                            value=1 / len(passengers)
                        )
                        for passenger in passengers
                    },
                    status_callback=get_http_api_url(endpoint="/order/%s/split_bill/callback" % order.id),
                    contribute_before=earliest_price.expired_at
                ),
                partner_request_id=partner_request,
                submit=True,
                identity_provider=user_identity_provider
            )
        except Exception as e:
            logger.error("Failed to create split_bill for order %s", order.id)
            order.status = RideHailingOrderStatus.ERROR
            # ? 为什么可以正常工作，_DB_SCHEMA是PrivAttr包裹的啊...
            supabase_db.update(
                schema=cls._DB_SCHEMA, table_name=cls._TABLE, 
                to_update={"status": order.status.value}, 
                filters=(('eq', ("_id", order.id)),) ,
                logger=logger
            )
            raise e
        else:
            # 4.2 关联平账账单
            split_bill_id = split_bill_create_res.body.split_bill.id
            order.split_bill = split_bill_id
            supabase_db.update(
                schema=cls._DB_SCHEMA, table_name=cls._TABLE,
                to_update={"split_bill": split_bill_id}, 
                filters=(('eq', ("_id", order.id)),),
                logger=logger
            )

            # 4.3 使用支付者（助理账号）的权限，认可该账单的审批
            try:
                v1_chat_approve_approval(
                    approval_id=split_bill_create_res.body.split_bill.approval,
                    identity_provider=get_assistant_identity_provider()
                )
            except Exception as e:
                logger.warning("Failed to approve split_bill %s's approval as payer", split_bill_id)

        # 5. 后续任务
        # 5.1 回调到搭子请求
        send_status_callback_to_pr.delay(order.id)

        return OrderManager(**order.dump_as_dict())

    def __is_placeable(self):

        """
        是否可以下单

        不可以则抛出异常

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Place
        """

        # 1. 必须处于草稿状态
        if self.status != RideHailingOrderStatus.PENDING:
            raise DuplicateOrConflict("order status", self.id, "must be draft")
        
        # 2. 绑定的平账账单是否所有贡献者已经支付
        is_contributed = v1_split_bill_is_status(
            split_bill_id=self.split_bill,
            status=SplitBillStatus.CONTRIBUTED,
            identity_provider=get_assistant_identity_provider()
        ).body.root
        if not is_contributed:
            raise DuplicateOrConflict("split_bill status", self.split_bill, "must be contributed")
        
    def __refresh_competitors_price_info(
        self, provider_id: ServiceProviderID, competitors: List[Competitor]
    ) -> None:

        """
        刷新Competitors的价格信息

        根据ride_type, route, preference，调用estimate_price，获取新的价格信息；
        更新新的价格信息到competitors中；
        """
        logger.info("Refreshing competitors of %s's price info", provider_id)

        provider_manager = get_service_provider_manager(provider_id)
        new_prices_info = provider_manager.estimate_price(
            route=self.route,
            ride_types=[competitor.ride_type for competitor in competitors],
            preference=self.preference
        )
        for new_price_info in new_prices_info:
            for competitor in competitors:
                if competitor.ride_type == new_price_info.ride_type:
                    competitor.update_price_info(price_info=new_price_info)
        
    def __place_competitors(
        self, provider_id: ServiceProviderID, competitors: List[Competitor], retry_times: int = 0
    ) -> bool:

        """
        将Competitors列表中的一个服务供应商的系列competitor全部下单

        :param retry_times: 重试次数；最多一次

        :return bool：是否成功
        """
        logger.info('Placing competitors of %s', provider_id)

        if retry_times > 1:
            logger.error("Failed to place competitors of %s after %s retries", provider_id, retry_times)
            return False

        try:
            provider = get_service_provider_manager(provider_id)

            # 下单到服务商
            sp_order_manager = provider.place_order(
                route=self.route, preference=self.preference, prices=competitors,
                order_manager=self
            )
        except PriceInfoExpired:
            # 价格信息过期，重新计算后重新下单
            self.__refresh_competitors_price_info(competitors)
            return self.__place_competitors(provider_id, competitors, retry_times + 1)
        except Exception as e:
            # 错误则标记该竞争者为需要移除
            logger.warning("Failed to place order to provider %s, error %s", provider_id, e)
            return False
        else:
            for competitor in competitors:
                competitor.service_provider_order_id = sp_order_manager.id
        
        return True

    def place(self):

        """
        下单（将订单下达至服务提供商）

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Place
        """
        logger.info("Place order %s", self.id)

        # 1. validation
        # 1.1 is placeable
        self.__is_placeable()

        # 2. place to service providers
        # 2.1 place order to each service provider
        to_be_removed: List[ServiceProviderID] = []
        for provider_id, competitors in self.competitors.items():
            if not self.__place_competitors(provider_id, competitors, to_be_removed):
                to_be_removed.append(provider_id)
        
        # 2.2 remove failed competitors
        for provider_id in to_be_removed:
            self.competitors.pop(provider_id)
        # 2.3 
        if len(self.competitors) == 0:
            # 2.3.1 if all failed, cancel the order
            self.cancel(
                reason=PlatformCancelReason.COMPETITORS_EXPIRD
            )
            self.update_to_db("competitors")
            # TODO a better exception type 
            raise ParamsInvalid("competitors", self.competitors, "all competitors are expired or invalid", logger=logger)
        else:
            # 2.3.2 status to dispatching
            self.status = RideHailingOrderStatus.DISPATCHING
            # 2.3.3 update timeline
            self.timeline["dispatch"] = get_datetimez()
        
        # 3. update to db
        self.update_to_db("status", "competitors", "timeline")

        # 4. 后续任务
        # 4.1 状态更新回调到搭子请求
        send_status_callback_to_pr.delay(self.id)

    @property
    def driven_route(self) -> DrivenRoute | None:

        """
        司机当前行驶路线

        仅在接客、送客时存在
        """
        return self.service_provider_instance.driven_route

    @property
    def navigation_info(self) -> NavigationInfo | None:

        """
        导航信息（司机位置+剩余信息+速度）

        仅在接客、送客时存在
        """
        return self.service_provider_instance.navigation_info

    @property
    def cancel_fee(self) -> int:

        """
        查询取消费用

        只有派单之后，才可能产生取消费，在这之前都是0

        如果已经取消，则是实际的取消费用 \n
        如果还未取消，则是预估的取消费用

        :return: int 取消费用（分） -1代表不可以取消
        """
        if self.status in (RideHailingOrderStatus.PENDING, RideHailingOrderStatus.DISPATCHING, RideHailingOrderStatus.COMPETING):
            return 0
        return self.service_provider_instance.cancel_fee

    def cancel(
        self, 
        reason: RideHailingOrderCancelReason,
        detail: str | None = None,
        cancelled_by: str | None = None
    ):

        """
        取消订单

        有这几种取消情况需要处理：\n
        1. 在下单之前取消：此时平账账单无法被回调触发取消，需要在此处取消平账账单 \n
        2. 在接单之前取消：分别取消每个竞争者的订单
        3. 在接单之后取消：正常流程

        :param reason: 取消原因代码
        :param detail: 取消原因详情（不提供则i18n取消原因代码）
        :param cancelled_by: 取消发起者（默认为None，说明不是乘客取消）

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Cancel
        """
        logger.info("Cancel order %s" % self.id)

        # 0. validation
        # can't be [CLOSED, ERROR, REVIEW_OPENING, UNPAID, CANCELLED]
        if self.__is_closed or self.__is_closing:
            raise DuplicateOrConflict("order status", self.status, "can't be cancelled")

        # 1. 取消对应服务提供商的订单
        # 1.1 调用SP的取消订单能力（如果已经竞争结束）
        if not self.__is_before_competed:
            detail = detail or reason.translate()
            cancel_fee = self.service_provider_instance.cancel_order(reason, detail)
        else:
            cancel_fee = 0
            if self.status != RideHailingOrderStatus.PENDING:
                # 1.3 如果是在派单后，竞争结束前，需要取消每个竞争者的订单
                for sp_id, competitors in self.competitors.items():
                    try:
                        sp_ins = get_service_provider_manager(sp_id)(competitors[0].service_provider_order_id)
                        cancel_fee += sp_ins.cancel_order(
                            reason=reason, detail=detail
                        )
                    except Exception as e:
                        logger.warning("Failed to cancel provider %s's order", sp_id)
                        continue
            # 1.2 如果是在派单前，则无操作

        # 3. 更新cancel_reason与timeline
        self.cancel_reason = reason
        self.timeline["cancel"] = get_datetimez()

        # 4.
        # 4.1 如果有取消费
        if cancel_fee > 0:
            pass # 什么都不做，等待服务提供商的未支付回调
        # 4.2 如果没有取消费，直接更新状态为cancelled，并更新cancel_reason, timeline
        else:
            # 4.2.2 取消平账账单（后台任务）
            # （只要能取消本订单，则说明还没有上报已支付事件，则平账账单是可以被取消的，我们也应该在没有取消费的情况下退款）
            cancel_split_bill.delay(self.id)

            self.status = RideHailingOrderStatus.CANCELLED

        # 5. update to db
        if cancelled_by:
            self.cancelled_by = cancelled_by
        self.update_to_db("status", "cancel_reason", "timeline", "cancelled_by")

        # 6. 后续任务
        # 6.1 状态更新回调到搭子请求
        send_status_callback_to_pr.delay(self.id)
    
    def __cancel_if_possible(self):

        """
        当条件满足，进行取消操作；不同条件代表不同的取消原因

        - 竞争者为空；说明全部都无司机接单，取消整个订单
        """
        if not self.competitors:
            self.cancel(
                reason=PlatformCancelReason.COMPETITORS_UNRESPONSIVE
            )

    def review(self, rating: int = 5, comment: str | None = None):

        """
        评价订单

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Review
        """
        logger.info("Review order %s" % self.id)

        # 1. 调用SP的评价订单能力
        self.service_provider_instance.review_order(rating, comment)

        # 2. status to closed
        self.status = RideHailingOrderStatus.CLOSED
        self.update_field_to_db("status")

        # 3. 后续任务
        # 3.1 状态更新回调到搭子请求
        send_status_callback_to_pr.delay(self.id)

    def sync(self, 
        exclude: List[Literal['timeline', 'fare']] = ('fare',),
        service_provider_instance: ServiceProviderManager = None
    ):

        """
        同步（从服务商端订单更新本订单信息）

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/Sync
        """
        logger.info("Syncing order info with service_provier %s", self.id)

        # 1.由服务供应商进行同步
        # 1.1 get service provider instance
        # raw_status = self.status
        if not service_provider_instance:
            service_provider_instance = self.service_provider_instance
        # 1.2 sync from service provider
        service_provider_instance.sync(order_manager=self)

        # 2. 更新到数据库
        self.update_to_db()

        # 3. 
        # 状态更新不会导致回调，不然可能导致冲突
        # 因为服务提供商会发送回调

        # 4. 后续任务
        # 4.1 状态更新回调到搭子请求 （不一定有更新，但是回调肯定ok）
        send_status_callback_to_pr.delay(self.id)

    @property
    def __is_before_competed(self) -> bool:

        """
        是否处于竞争结束前
        """
        return self.status in (
            RideHailingOrderStatus.PENDING, 
            RideHailingOrderStatus.DISPATCHING, 
            RideHailingOrderStatus.COMPETING,
            RideHailingOrderStatus.PENDING
        )
    
    @property
    def __is_closed(self) -> bool:
            
        """
        是否已经关闭（无论正常与否）
        """
        return self.status in (
            RideHailingOrderStatus.CLOSED, 
            RideHailingOrderStatus.CANCELLED,
            RideHailingOrderStatus.REVIEW_OPENING
        )
    
    @property
    def __is_closing(self) -> bool:
            
        """
        是否结算中
        """
        return self.status in (
            RideHailingOrderStatus.UNPAID,
        )

    def __compete(self) -> Competitor:

        """
        竞争
        """
        # TODO

    def handle_callback(self, callback: OrderCallback):

        """
        处理回调事件（总入口）

        :param callback: 回调事件

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/Order/HandleCallback
        """
        
        # 判断回调事件类型，调用对应处理器
        if callback.type == OrderCallbackType.SP_ORDER_STATUS_UPDATE:
            self.__handle_sp_order_status_update(callback)
        elif callback.type == OrderCallbackType.SPLIT_BILL_STATUS_UPDATE:
            self.__handle_split_bill_status_update(callback)
        else:
            logger.warning("Unknown callback type %s", callback.type)

    def __handle_sp_order_status_update(self, callback: OrderCallback):

        """
        处理服务提供商订单状态更新事件
        """
        # 1. 根据状态调用对应处理器
        new_status = callback.content.new_status
        handler = self._SP_ORDER_STATUS_UPDATE_HANDLER_MAPPER.get(new_status)
        if handler:
            handler(self=self, callback=callback)
        else:
            logger.warning("No handler for status %s", new_status)

            # 2. 同步订单信息
            # 2.1 前提：不可以处于竞争结束前
            # 2.2 前提：必须是竞争结束后，获胜的服务提供商的回调
            if not self.__is_before_competed:
                if callback.content.service_provider_id == self.service_provider_id:
                    # 必须确保是获胜者才同步，不然数据就错误了（因为指定了instance）
                    logger.info("Just sync order info")
                    self.sync(service_provider_instance=callback.content.instance)
                    return
            
            logger.warning("Can't sync order info before competed or this is not the winner's callback")

    def __handle_split_bill_status_update(self, callback: OrderCallback):

        """
        处理平账账单状态更新事件
        """
        logger.info("Handle split bill status update of order %s", self.id)

        # 根据通知的状态调用对应处理器
        status = callback.content.new_status
        handler = self._SPLIT_BILL_STATUS_UPDATE_HANDLER_MAPPER.get(status)
        if handler:
            handler(self=self)
        else:
            logger.warning("No handler for split_bill status %s", status)

    def __handle_accepted(self, callback: OrderCallback):

        """
        处理已接单(Accepted)状态

        只有处于竞争结束前的状态才处理 \n
        （accepted, picking_up, arrived都会触发该函数，防止反复触发）
        """
        logger.info("Handle accepted status of order %s", self.id)

        # 0. validation
        # status must be [Pending, Dispatching, Competing]
        if not self.__is_before_competed:
            logger.error("Order %s status is not pending, dispatching or competing, can't process accepted callback", self.id)
            return

        # 1. compete
        # 1.1 是否有多个服务提供商竞争
        if len(self.competitors) > 1:
            # 调用compete，取得胜出者（会同时取消所有失败者订单）
            # TODO 这样调用是不行的，需要变为一个任务
            winner = self.__compete()
        else:
            # 只有一个服务提供商，直接将当前回调通知的服务提供商作为胜出者
            winner = callback.content.instance.winner

        # 2. 更新数据
        # 2.1 设置competitors为空
        self.competitors = {}
        # 2.2 设置ride_type, service_provider_order_id为胜出的车型与对应的服务商订单ID
        self.ride_type = winner.ride_type
        self.service_provider_order_id = winner.service_provider_order_id
        # 2.3 更新状态 根据新状态来设置（可能是accepted或者picking_up）
        self.status = callback.content.new_status
        # 2.4 更新timeline
        self.timeline["accept"] = get_datetimez()

        # 3. 更新到数据库
        self.update_to_db("ride_type", "service_provider_order_id", "competitors", "status", "timeline")

        # 4. 发送回调到PR
        send_status_callback_to_pr.delay(self.id)

    def __handle_unpaid(self, callback: OrderCallback):

        """
        处理未支付(Unpaid)状态

        只有处于竞争结束之前、关闭以外的状态才可以处理
        """
        logger.info("Handle unpaid status of order %s", self.id)

        # 0. validation
        # status must not be [Pending, Dispatching, Competing, Closed, Cancelled, ReviewOpening or Unpaid]
        if self.__is_before_competed or self.__is_closed or self.__is_closing:
            logger.error("Order %s status is pending, dispatching, competing or closed, can't process unpaid callback", self.id)
            return

        # 1. 同步费用信息
        total, details = callback.content.instance.fare
        try:
            v1_split_bill_prepay_paid(
                split_bill_id=self.split_bill,
                body=V1SplitBillPrepayPaidRequestBody(
                    paid_at=time.time(), 
                    payee=callback.content.service_provider_id.translate(),
                    actual=total, 
                    proof="ride_hailing/order/plcae?id=%s" % self.id,  # TODO 使用前端页面地址获取器
                    details=[detail.to_split_bill_detail() for detail in details]
                ),
                identity_provider=get_assistant_identity_provider()
            )
        except DuplicateOrConflict:
            logger.warning("Failed to update split_bill %s as paid, maybe already marked as paid", self.split_bill)
        else:
            # 2. 更新状态为未支付款项
            self.status = RideHailingOrderStatus.UNPAID
            self.update_field_to_db("status")

            # 2.2 回调到搭子请求
            send_status_callback_to_pr.delay(self.id)

    def __handle_cancelled(self, callback: OrderCallback):

        """
        处理已取消(Cancelled)状态

        只有在处于取消、关闭以外的状态才可以处理
        """
        logger.info("Handle cancelled status of order %s", self.id)

        # 0. validation
        # status must not be [Cancelled, Closed]
        if self.status in (RideHailingOrderStatus.CANCELLED, RideHailingOrderStatus.CLOSED):
            logger.error("Order %s status is cancelled or closed, can't process cancelled callback", self.id)
            return
        
        # 1. 如果处于竞争结束前，则移除该竞争者
        if self.__is_before_competed:
            self.competitors.pop(callback.content.service_provider_id)
            self.update_to_db("competitors")
        
        # 2. 其它状态不需要额外处理
        pass

        # 3. cancel if possible
        self.__cancel_if_possible()

    def __handle_split_bill_contributed(self):

        """
        处理平账账单所有贡献者已支付(Contributed)状态
        """
        logger.info("Handle split bill contributed of order %s", self.id)

        # 1. 如果状态为Draft，则说明创建订单后没有下单，恢复过程
        if self.status == RideHailingOrderStatus.PENDING:
            self.place()
        # 2. 如果状态为Unpaid，则按照closed的逻辑处理（这其实是不可能的？）
        elif self.status == RideHailingOrderStatus.UNPAID:
            self.__handle_split_bill_closed()

    def __handle_split_bill_closed(self):

        """
        处理平账账单已关闭(Closed)状态
        """
        logger.info("Handle split bill closed of order %s", self.id)

        # 0. Validation
        # 0.1 状态必须为Unpaid
        if self.status != RideHailingOrderStatus.UNPAID:
            logger.error("Order %s status is not Unpaid", self.id)
            return
        
        # 1. 确认费用
        self.service_provider_instance.confirm_fare()
        
        # 2. update status
        # 2.1 如果有取消原因，则更新状态为Cancelled
        if self.cancel_reason:
            self.status = RideHailingOrderStatus.CANCELLED
        # 2.2 正常接单，进入ReviewOpening
        else:
            self.status = RideHailingOrderStatus.REVIEW_OPENING

        # 3. update timeline
        self.timeline['pay'] = get_datetimez()

        # 4. update to db
        self.update_to_db("status", "timeline")
        send_status_callback_to_pr.delay(self.id)

    def __handle_split_bill_cancelled(self):

        """
        处理平账账单已取消(Cancelled)状态
        """
        logger.info("Handle split bill cancelled of order %s", self.id)

        # 1. 调用取消接口
        try:
            self.cancel(
                reason=PlatformCancelReason.PAYMENT_TIMEDOUT
            )
        except DuplicateOrConflict as e:
            # 已经取消，无需再处理（无论是取消订单导致还是重复，都无需再处理）
            logger.warning("Order %s has been cancelled", self.id)

        # 2. 后续任务
        # 2.1 状态更新回调到搭子请求
        send_status_callback_to_pr.delay(self.id)

    def __handle_split_bill_rejected(self):

        """
        处理平账账单已拒绝(Rejected)状态
        """
        logger.info("Handle split bill rejected of order %s", self.id)

        # 1. 如果为Pending，则取消订单（但不用进一步取消平账账单）
        if self.status == RideHailingOrderStatus.PENDING:
            self.cancel(
                reason=PassengerCancelReason.PARTNER_REJECTED,
                # TODO 记录取消人
            )
        # 2. 如果为其它状态，说明异常
        else:
            logger.error("Order %s status is not Pending, it's %s", self.id, self.status)
            self.status = RideHailingOrderStatus.ERROR
            self.update_to_db("status")

    _SP_ORDER_STATUS_UPDATE_HANDLER_MAPPER: Dict[RideHailingOrderStatus, Callable] = {
        RideHailingOrderStatus.ACCEPTED: __handle_accepted,
        RideHailingOrderStatus.PICKING_UP: __handle_accepted,  # 因为不是按照通知事件，而是最新状态处理
        RideHailingOrderStatus.UNPAID: __handle_unpaid,
        RideHailingOrderStatus.CANCELLED: __handle_cancelled,
    }

    _SPLIT_BILL_STATUS_UPDATE_HANDLER_MAPPER: Dict[SplitBillStatus, Callable] = {
        SplitBillStatus.CONTRIBUTED: __handle_split_bill_contributed,
        SplitBillStatus.CLOSED: __handle_split_bill_closed,
        SplitBillStatus.CANCELLED: __handle_split_bill_cancelled,
        SplitBillStatus.REJECTED: __handle_split_bill_rejected,
    }
