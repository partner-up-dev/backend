"""
author: Lan_zhijiang
date: 2024-10-22
desc: 曹操出行（服务提供商） 管理器
issues: 
    #2
references: 
    https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/ServiceProvider/Caocao
"""

# typing
from typing import Dict, List, Literal, Tuple, TypeVar

# typing - business module
from app.schemas.order import Competitor, DriverInfo
from app.schemas.order.price import (
    PriceDetail,
    RideHailingOrderFareType
)
from app.schemas.order.config import Purpose
from app.managers.service_provider import ServiceProviderManager
from app.schemas.service_provider import ServiceProvider
from app.schemas.service_provider.caocao import (
    CaocaoOrder, CaocaoOrderType, CaocaoCancelCode, CaocaoOrderStatus
)
from app.schemas.base.route import Location, Route, DrivenRoute, NavigationInfo
from app.schemas.order.price import PriceInfo
from app.schemas.service_provider.caocao.price import CaocaoLineType, CaocaoOrderTag
from app.schemas.service_provider.caocao.availiablity import CityAvailability
from app.schemas.service_provider.caocao.base import OnOff
from app.schemas.order.config import RideType
from app.schemas.service_provider.caocao.callback import (
    CaocaoCallback
)
from app.schemas.service_provider.caocao.config import CaocaoCarType
from app.schemas.order.callback import (
    OrderCallbackType, OrderCallback, SPOrderStatusUpdateContent
)

# api
from app.schemas.service_provider.caocao.response import ResponseBody as CaocaoResponseBody
from app.schemas.service_provider.caocao.response import (
    getAllCitiesData, queryCityData, estimatePriceWithDetailResponseData,
    orderCarResponseData, cancelOrderResponseData,
    queryCancelFeeResponseData, queryDriverPolylineResponseData,
    queryDriverLocationResponseData
)
from app.schemas.service_provider.caocao.request import (
    estimatePriceWithDetailRequestData,
    orderCarRequestData, serviceTypePrice,
    queryOrderDetailRequestData, 
    cancelOrderRequestData, whoCancel,
    queryCancelFeeRequestData,
    feeConfirmRequestData, 
    queryDriverPolylineRequestData, navigationPolylineType,
    queryDriverLocationRequestData
)

# interface_main api
from interface_main.apis.account import v1_account_get_phone

# managers
from app.managers.route import LocationManager
from app.managers.order.config import RideTypeManager

# lib
import requests
import hashlib
import time
import datetime
from data.settings.models.caocao import get_setting as get_caocao_setting
from app.libs.exceptions import ServerException, ParamsInvalid, Unauthorized, DuplicateOrConflict, NotFound, PriceInfoExpired
from requests import HTTPError

# util
from app.utils.cache import SimpleCache
from app.utils.auth import get_assistant_identity_provider
from backend_common.utils.request import get_form_data
from backend_common.utils.datetime import get_datetimez
from backend_common.utils.pydantic import get_pri_attr_value

# logger
from backend_common.libs.logs import top_logger as logging
logger = logging.getChild("CaocaoManager")


class CaocaoManager(ServiceProviderManager[str, CaocaoOrderStatus], CaocaoOrder):

    """
    服务供应商-曹操出行管理器

    合并了APIClient + OrderManager的职能
    """

    _SERVICE_PROVIDER_ID = ServiceProvider.CAOCAO

    _BASE_URL = get_caocao_setting().base_url
    _CLIENT_ID = get_caocao_setting().client_id
    _SIGN_KEY = get_caocao_setting().sign_key

    def __init__(self, id_ = None, **data):
        super().__init__(id_, **data)

        self._ROUTE_INFO_CACHE = SimpleCache[queryDriverPolylineResponseData](
        )
        self._ROUTE_INFO_CACHE.set_refresher(lambda: self.route_info)
        self._ROUTE_INFO_CACHE.set_expired_in(5)

    @property
    def inner_status(self) -> CaocaoOrderStatus:
        return self.basicOrderVO.status

    @staticmethod
    def timestamp_to_datetime(timestamp: float | None) -> str:

        """
        将时间戳转换为曹操出行认可的datetime字符串

        时间戳并未带有时区信息，默认为UTC+8

        WARN 小心时区问题
        """
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    
    @staticmethod
    def datetime_to_timestamp(datetime: str) -> float:
            
        """
        将曹操出行认可的datetime字符串转换为时间戳

        时间戳并未带有时区信息，默认为UTC+8

        WARN 小心时区问题
        """
        return time.mktime(time.strptime(datetime, "%Y-%m-%d %H:%M:%S"))

    @classmethod
    def __sign_request(cls, data: dict):

        """
        签名请求

        Docs
        ----
        https://git.hadream.ltd/anana/backend/ride_hailing/-/wikis/ServiceProvider/Caocao/APIClient#%E7%AD%BE%E5%90%8D
        """
        copied = data.copy()
        # Add sign_key to the combined dictionary
        copied['sign_key'] = get_pri_attr_value(cls._SIGN_KEY)
        # Sort the dictionary by key
        sorted_combined = sorted(copied.items())
        # Create the original signature string
        original_string = ''.join(f'{key}{value}' for key, value in sorted_combined)
        # Encrypt the original string using sha1 and return the hex digest
        signature = hashlib.sha1(original_string.encode('utf-8')).hexdigest()

        return signature

    @classmethod
    def __base_request(
        cls, method: Literal['GET', 'POST'], endpoint: str, 
        data: dict = None
    ) -> CaocaoResponseBody:
        
        """
        曹操出行API请求 基础方法

        :param data: GET时作为query，POST时作为body(x-www-form-urlencoded)

        该函数会自动添加client_id, timestamp(ms int)两个参数；\n
        并对请求进行签名
        """
        logger.info(f"Requesting Caocao API: {endpoint}")

        if data is None:
            data = {}

        # Add client_id and timestamp to data
        data['client_id'] = get_pri_attr_value(cls._CLIENT_ID)
        data['timestamp'] = int(time.time() * 1000)

        # Sign the request
        data['sign'] = cls.__sign_request(data)

        # Send the request
        try:
            base_url = get_pri_attr_value(cls._BASE_URL)
            if method == 'GET':
                res = requests.get(
                    base_url + endpoint, params=data
                )
            elif method == 'POST':
                res = requests.post(
                    base_url + endpoint, data=data
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
        except HTTPError as e:
            raise ServerException(500, f"Request failed with http error: {e}", logger=logger)
        else:
            # handle response
            if res.status_code == 200:
                res_body = CaocaoResponseBody(**res.json())

                if res_body.code == 200:
                    if res_body.success:
                        return res_body
                if res_body.code == 406:
                    # sign check failed -> 500
                    raise ServerException(500, "caocao sign check failed, report this to maintainers", logger=logger)
                if res_body.code == 461 or res_body.code == 23005:
                    # price info expired
                    raise PriceInfoExpired(logger=logger)

                raise ServerException(500, f"caocao api failed with code {res_body.code}, {res_body.msg}", logger=logger)
            else:
                raise ServerException(500, f"Request failed to sent to caocao api with status code {res.status_code}", logger=logger)

    @classmethod
    def __get_cities_availability(cls) -> Dict[str, CityAvailability]:

        """
        获取城市服务开通状态（全量获取）

        https://app.apifox.com/link/project/5283937/apis/api-224155442
        """
        logger.info("Querying cities availability")

        temp: dict = cls.__base_request('GET', '/common/getAllCities').data
        result: Dict[str, CityAvailability] = {}
        for city_availiabity in getAllCitiesData(**temp).cities:
            result[city_availiabity.cityCode] = city_availiabity

        return result
    
    _CITIES_AVAILABILITY_CAHCE = SimpleCache[Dict[str, CityAvailability]]()
    _CITIES_AVAILABILITY_CAHCE.set_refresher(lambda: CaocaoManager.__get_cities_availability())
    '''城市服务开通状态的缓存'''

    @classmethod
    def __get_city_code_by_location(cls, location: Location) -> str:

        """
        根据经纬度获取城市编码

        https://app.apifox.com/link/project/5283937/apis/api-224206252
        """
        logger.info(f"Querying city code by location: {location}")

        res: dict = cls.__base_request('GET', '/common/queryCity', {
            'latitude': location.lat,
            'longitude': location.lng
        }).data
        return queryCityData(**res).city_code
    
    @staticmethod
    def is_route_reservable(route: Route) -> bool:

        """
        判断当前路线配置的时间对于曹操出行来说是否算预约单

        判断 route[0].datetime[0] 与 当前时间（下单时间） 的差距：
            - 在前30分钟内，则为不可预约
            - 在前30分钟 - 前72小时内，则为预约单
            - 在前72小时以上，则为不可预约
            - 出发时间必须在下单时间之后
        """
        current_time = time.time()
        departure_time = route.root[0].datetime[0] / 1000 # TODO 后续改为datetime

        if current_time > departure_time:
            raise ParamsInvalid("departure time", departure_time, "after now")

        if 30 * 60 <= abs(current_time - departure_time) <= 72 * 60 * 60:
            return True
        
        return False
        
        
    @classmethod
    def is_available(cls, ride_type, route, preference, **kwargs) -> bool:
        
        """
        该车型在当前路线与配置条件下是否可用

        1. 判断车型是否在当前城市开通

        :param kwargs:
            city_code: 传入则不用再查询
        """
        logger.debug(f"Checking ride type availability: {ride_type}")

        # 1. 判断车型是否在当前城市开通
        city_code = kwargs.get("city_code")
        if not city_code:
            city_code = cls.__get_city_code_by_location(LocationManager(route.root[0].location))
        
        car_type = ride_type.car_type
        city_availiability = get_pri_attr_value(cls._CITIES_AVAILABILITY_CAHCE).get().get(city_code)
        if city_availiability:
            return city_availiability.is_car_type_available(car_type)
        else:
            logger.warning(f"City code {city_code} is not available at all")
            return False
        
    @staticmethod
    def is_price_info_valid(price_info):

        """
        判断price_key是否过期（有效期10分钟）（另外减少30s时间）
        """
        if abs(price_info.price_key - time.time()) > 570:
            return False
        return True
    
    @classmethod
    def get_from_to_lat_lng(
        cls, route, 
        departure_location: Location = None, arrival_location: Location = None
    ) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        
        """
        通过Route获取起点和终点的经纬度

        :returns (from_lat, from_lng), (to_lat, to_lng)
        """
        departure_location = LocationManager(route.root[0].location) if departure_location is None else departure_location
        arrival_location = LocationManager(route.root[-1].location) if arrival_location is None else arrival_location
        return (departure_location.lat, departure_location.lng), (arrival_location.lat, arrival_location.lng)
    
    @classmethod
    def get_city_code_by_location(cls, location: Location) -> str:
        
        """
        通过Location获取城市编码
        """
        return cls.__get_city_code_by_location(location)
    
    @classmethod
    async def resolve_callback(cls, request):
        
        # 1. validate signaure
        body = await get_form_data(request)
        callback_sign = body['sign']
        body.pop('sign')
        our_sign = cls.__sign_request(body)

        if our_sign != callback_sign:
            raise Unauthorized("Signature is invalid")
        
        # 2. convert to standard callback
        caocao_callback = CaocaoCallback(**{
            **body,
            "sign": callback_sign
        })
        # 2.1 what type
        if caocao_callback.event.is_status_updated:
            type = OrderCallbackType.SP_ORDER_STATUS_UPDATE

            # 2.2 获取最新状态，避免错误
            caocao_manager = cls(caocao_callback.order_id)  # 使用服务提供商ID进行查询

            content = SPOrderStatusUpdateContent(
                service_provider_order_id=caocao_callback.order_id,
                order_id=int(caocao_callback.ext_order_id),  # RELEASE
                # order_id=caocao_callback.ext_order_id.replace("partner-up-mock", ""),  # TEST
                new_status=caocao_manager.status,
                service_provider_id=get_pri_attr_value(cls._SERVICE_PROVIDER_ID),
                instance=caocao_manager
            )
        else:
            type = OrderCallbackType.UNKNOWN
            content = None
        # 2.3 compose standard callback
        # WARN potential timezone issue
        callback = OrderCallback(
            timestamp=get_datetimez(timestamp=caocao_callback.timestamp/1000),
            type=type,
            content=content
        )

        return callback

    @classmethod
    def get_available_ride_types(cls, route, preference = None):
        
        # 1. if railway_pickup,dropoff, none is available
        if preference:
            if preference.purpose in (Purpose.RAILWAY_DROPOFF, Purpose.RAILWAY_PICKUP):
                return []

        # 1. get city_code from route
        city_code = cls.__get_city_code_by_location(LocationManager(route.root[0].location))

        # 2. get all available ride types by city_code
        car_types: List[CaocaoCarType] = []
        city_availiability = get_pri_attr_value(cls._CITIES_AVAILABILITY_CAHCE).get().get(city_code)
        if city_availiability:
            car_types.extend(city_availiability.get_all_availiable_car_types())
        else:
            logger.warning(f"City code {city_code} is not available at all")
            return []
        
        ride_types = [
            RideTypeManager(car_type=car_type, service_provider=get_pri_attr_value(cls._SERVICE_PROVIDER_ID))
            for car_type in car_types
        ]

        return ride_types


    @classmethod
    def fetch_by_id(cls, id_, *fields, **kwargs) -> dict:

        """
        通过曹操的查询订单接口获取订单数据，不支持指定字段
        """
        logger.debug(f"Fetching order data by id: {id_}")

        data = queryOrderDetailRequestData(order_id=id_)

        res: dict = cls.__base_request('GET', '/common/queryOrderDetailV2', data.model_dump(exclude_unset=True)).data
        return res

    @classmethod
    def estimate_price(cls, route, ride_types, preference = None, **kwargs) -> List[PriceInfo]:
        
        """
        曹操出行的预估价格
        
        转换为标准价格信息返回; \n
        如果车型不可用，则忽略（所以返回长度不一定等于ride_types）

        :param kwargs: 
            passenger_num: 乘客数量，不传递默认为2，不为int则抛出错误

        https://app.apifox.com/link/project/5283937/apis/api-224225061
        """
        logger.info(f"Estimating price for route: {route}")
        result: List[PriceInfo] = []
        query_batch: List[List[RideType]] = []

        # 1. prepare data
        # 1.1 from/to_latitude & from/to_longitude
        departure_location = LocationManager(route.root[0].location)
        arrival_location = LocationManager(route.root[-1].location)
        from_latitute, from_longitude = departure_location.lat, departure_location.lng
        to_latitute, to_longitude = arrival_location.lat, arrival_location.lng

        # 1.2 计算城市编码
        city_code = cls.get_city_code_by_location(departure_location)

        # 1.3 计算订单类型
        order_type = CaocaoOrderType.from_preference(preference=preference)

        # 1.4 预约
        # 1.4.1 是否可以预约（如果配置了preference且检查到要求预约）
        if order_type.is_reserving:
            if not cls.is_route_reservable(route):
                # 是预约类型单不可以预约，则抛出异常
                raise ParamsInvalid("departure_time", route.root[0].datetime[0] / 1000, "after now 30min ~ 72h") 
        # 1.4.2 是否为预约（没有配置preference）
        if not preference:
            if cls.is_route_reservable(route):
                order_type = CaocaoOrderType.SCHEDULED

        # 1.5 去除不可用车型
        ride_types = [ride_type for ride_type in ride_types if cls.is_available(ride_type, route, preference, city_code=city_code)]

        # 1.6 将允许拼车的ride_type独立出来
        query_batch.append([ride_type for ride_type in ride_types if not ride_type.carpool])
        query_batch.append([ride_type for ride_type in ride_types if ride_type.carpool])

        # 2. compose data and query
        for i in range(2):

            if not query_batch[i]:
                continue

            passenger_num = kwargs["passenger_num"] if "passenger_num" in kwargs else 2
            if not isinstance(passenger_num, int):
                raise ParamsInvalid("passenger_num", passenger_num, "int")
            
            data = estimatePriceWithDetailRequestData(
                city_code=city_code,
                from_latitude=from_latitute, from_longitude=from_longitude,
                to_latitude=to_latitute, to_longitude=to_longitude,
                order_type=order_type, 
                car_type=','.join([str(ride_type.car_type.value) for ride_type in query_batch[i]]),
                carpool_type=OnOff.ON if i == 1 else OnOff.OFF,
                count_person=passenger_num
            )
            if order_type.is_reserving:
                data.departure_time = cls.timestamp_to_datetime(route.root[0].datetime[0] / 1000)

            res: dict = cls.__base_request(
                'GET', '/common/estimatePriceWithDetail', data.model_dump(exclude_unset=True)).data
            res: estimatePriceWithDetailResponseData = estimatePriceWithDetailResponseData(root=res)
            
            # 3. compose price info
            for item in res.root:
                # 根据car_type计算ride_type
                try:
                    ride_type = [ride_type for ride_type in query_batch[i] if ride_type.car_type == item.carType][0]
                except IndexError:
                    # impossible
                    logger.warning(f"Cannot find original ride_type of carType {item.carType}")
                    continue

                result.append(PriceInfo(
                    ride_type=ride_type.id,
                    price_key=item.priceKey,
                    type=item.lineType.to_fare_type(),
                    total=item.originPrice,
                    actual=item.price,
                    details=[
                        detail_item.to_standard() for detail_item in item.detail
                    ],
                    # 5min - 20s with timezone info
                    expired_at=get_datetimez() + datetime.timedelta(seconds=280)
                ))

        return result
            
    @classmethod
    def place_order(cls, route, preference, prices, order_manager) -> 'CaocaoManager':
        
        logger.info(f"Placing order of: {route}")
        
        # 1. get information from route
        departure_location = LocationManager(route.root[0].location)
        arrival_location = LocationManager(route.root[-1].location)
        # 1.1 from/to_latitude & from/to_longitude
        (from_latitute, from_longitude), (to_latitute, to_longitude) = cls.get_from_to_lat_lng(
            route, departure_location=departure_location, arrival_location=arrival_location
        )
        
        # 1.2 city code
        city_code = cls.get_city_code_by_location(departure_location)

        # 1.3 start,end_name & start,end_address
        start_name, end_name = departure_location.friendly_address, arrival_location.friendly_address
        start_address, end_address = \
            departure_location.friendly_address + '(' + ','.join(departure_location.address[-2:]) + ')', \
            arrival_location.friendly_address + '(' + ','.join(arrival_location.address[-2:]) + ')'

        # 2. get information from order_manager
        # 2.1 ext_orer_id
        ext_order_id = order_manager.id

        # 2.2 caller_phone & passenger_phone
        # 2.2.1 get caller and passenger
        caller: str = order_manager.caller
        passenger: str | None = order_manager.passengers[1] if len(order_manager.passengers) > 1 else None

        # 2.2.2 get caller, passenger phone & passenger_name from account
        try:
            caller_phone = v1_account_get_phone(caller, identity_provider=get_assistant_identity_provider()).body.root  # TODO 未来区号可能导致问题吗？
        except NotFound:
            # not allowed behavior
            raise ParamsInvalid('caller phone', None, 'caller phone is required')

        try:
            passenger_phone = v1_account_get_phone(passenger, identity_provider=get_assistant_identity_provider()).body.root if passenger else None
        except NotFound:
            # fine
            passenger_phone = None
        
        # passenger_name = None

        # 2.3 type -> order_type
        order_type = CaocaoOrderType.from_standard(order_manager.type, cls.is_route_reservable(route))

        # 2.4 fare_type -> line_type, order_tag
        line_type = CaocaoLineType.from_standard(order_manager.fare_type)
        order_tag = CaocaoOrderTag.from_standard(order_manager.fare_type)

        # 3. 根据订单类型，再获取其它信息
        # 3.1 如果是预约单，则需要departure_time
        departure_time = route.root[0].datetime[0] / 1000 if order_type == CaocaoOrderType.SCHEDULED else None

        # 3.2 如果是接送机单，则需要flight_no, fli_takeoff_time
        flight_no = None
        flt_takeoff_time = None
        if order_type in (CaocaoOrderType.AIRPORT_DROPOFF, CaocaoOrderType.AIRPORT_PICKUP):
            flight_no = preference.flight
            # TODO V1TravelGetFlight
            flt_takeoff_time = ""  # YYYY-MM-DD HH:mm:ss            

        # 4. 整理prices为serivice_type_prices
        ride_types: Dict[str, RideTypeManager] = {
            price.ride_type: RideTypeManager(price.ride_type) for price in prices
        }
        service_type_prices = [
            serviceTypePrice(
                serviceType=ride_types[price.ride_type].car_type,
                estimatePrice=price.actual,
                estimateKey=price.price_key
            ) for price in prices
        ]

        # 5. 处理ride_type中的非曹操出行对应配置
        # 5.1 任何一个ride_type中配置了允许拼车、接力单与联盟运力都会导致整个订单采用该配置
        accept_cp_driver = OnOff.OFF
        accept_relay_order = OnOff.OFF
        carpool_type = OnOff.OFF
        for ride_type in ride_types.values():
            # WARN potenial performance issue
            # ride_type = RideTypeManager(price.ride_type)
            ride_type = ride_type.schema
            if ride_type.carpool:
                carpool_type = OnOff.ON
            if ride_type.league:
                accept_cp_driver = OnOff.ON
            if ride_type.relay:
                accept_relay_order = OnOff.ON

            if carpool_type == OnOff.ON and accept_cp_driver == OnOff.ON and accept_relay_order == OnOff.ON:
                break

        # 6. compose request data
        data = orderCarRequestData(
            ext_order_id=str(ext_order_id),  # RELEASE
            # ext_order_id=str(ext_order_id) + "partner-up-mock", # TEST
            from_latitude=from_latitute, from_longitude=from_longitude,
            to_latitude=to_latitute, to_longitude=to_longitude,
            caller_phone=caller_phone, 
            city_code=city_code, order_type=order_type,
            start_name=start_name, start_address=start_address, end_name=end_name, end_address=end_address,
            service_type_price=service_type_prices, 
            is_simultaneously_call=OnOff.ON
        )
        if passenger_phone:
            # 此时passenger_phone被视为验证手机号，实际上应该是caller；所以调换
            data.caller_phone = passenger_phone
            data.passenger_phone = caller_phone
        # if passenger_name:
        #     data.passenger_name = passenger_name
        if line_type:
            data.line_type = line_type
        if order_tag:
            data.order_tags = order_tag
        if accept_cp_driver:
            data.accept_cp_driver = accept_cp_driver
        if accept_relay_order:
            data.accept_relay_order = accept_relay_order
        if carpool_type and len(order_manager.passengers) <= 2:
            data.carpool_type = carpool_type
            data.count_person = len(order_manager.passengers)
        if flight_no and flt_takeoff_time:
            # 两个都得要，不然就无效
            data.flight_no = flight_no
            data.flt_takeoff_time = flt_takeoff_time
        if order_type == CaocaoOrderType.SCHEDULED:
            data.departure_time = cls.timestamp_to_datetime(departure_time)

        # 7. send request
        res: dict = cls.__base_request('POST', '/common/orderCarV2', data.model_dump(exclude_unset=True)).data
        return cls(str(orderCarResponseData(**res).orderNo))

    @property
    def cancel_fee(self) -> int:

        """
        获取取消费用
        """
        logger.info(f"Querying cancel fee of order {self.id}")

        data = queryCancelFeeRequestData(order_no=self.id)
        try:
            res: dict = self.__base_request('GET', '/common/queryCancelFee', data.model_dump(exclude_unset=True)).data
        except Exception:
            logger.error(f"Failed to query cancel fee of order {self.id}")
            return -1
        else:
            res: queryCancelFeeResponseData = queryCancelFeeResponseData(**res)
            return res.cancelFee
        
    @classmethod
    def __cancel_order_cls(cls, order_id, reason, detail) -> int:
        
        logger.info(f"Cancelling order: {order_id}")

        # 1. get who_cancel and detail
        detail = detail if detail else reason.translate()
        try:
            who_cancel = whoCancel.from_standard_cancel_code(reason)
        except ValueError:
            who_cancel = None

        # 2. compose data
        data = cancelOrderRequestData(
            order_id=order_id,
            cancel_code=CaocaoCancelCode.from_standard(reason),
            cancel_reason=detail
        )
        if who_cancel:
            data.who_cancel = who_cancel

        # 3. request
        try:
            res: dict = cls.__base_request('POST', '/common/cancelOrderV3', data.model_dump(exclude_unset=True)).data
        except Exception:
            logger.error(f"Failed to cancel order: {order_id}")
            return -1
        else:
            res: cancelOrderResponseData = cancelOrderResponseData(**res)
            return res.cancelFee
        
    def cancel_order(self, reason, detail = None):
        return self.__cancel_order_cls(self.id, reason, detail)
        
    @classmethod
    def __confirm_fare_cls(cls, order_id, allowance = 0):
        
        logger.info(f"Confirming fare of order {order_id}")

        # compose request data
        data = feeConfirmRequestData(order_id=order_id)
        if allowance:
            data.allowance = allowance
        
        # request
        cls.__base_request('POST', '/common/feeConfirm', data.model_dump(exclude_unset=True))

    def confirm_fare(self, allowance = 0):
        self.__confirm_fare_cls(self.id, allowance)

    @classmethod
    def __get_route_info(cls, order_id: str, polyline_type: navigationPolylineType) -> queryDriverPolylineRequestData:

        logger.info(f"Getting route info of order {order_id}")

        # 1. compose data
        data = queryDriverPolylineRequestData(order_id=order_id, navigationPolylineType=polyline_type)

        # 2. request
        res: dict = cls.__base_request('POST', '/common/queryDriverPolyline', data.model_dump(exclude_unset=True)).data
        res: queryDriverPolylineResponseData = queryDriverPolylineResponseData(**res)

        return res
    
    @property
    def route_info(self) -> queryDriverPolylineRequestData:
        try:
            return self.__get_route_info(self.id, self.__get_route_type(self.id, self.inner_status))
        except DuplicateOrConflict:
            return None
    
    @classmethod
    def __get_route_type(cls, order_id: str, status: CaocaoOrderStatus) -> navigationPolylineType:

        route_type: navigationPolylineType | None = None

        # 1. get route_type from status
        status = status if status else CaocaoOrder(**cls.fetch_by_id(id_=order_id)).basicOrderVO.status
        # 1.1 get picking_up route if status is SERVICE_STARTED
        if status == CaocaoOrderStatus.DRIVER_ARRIVED:
            route_type = navigationPolylineType.WAITING
        elif status == CaocaoOrderStatus.SERVICE_STARTED:
            route_type = navigationPolylineType.PICKING_UP
        # 1.2 get dropping_off route if status is DRIVER_ARRIVED or SERVICE_ENDED
        elif status == CaocaoOrderStatus.PASSENGER_ONBOARD:
            route_type = navigationPolylineType.DROPPING_OFF
        else:
            raise DuplicateOrConflict("status", status, "must be DRIVER_ARRIVED, SERVICE_STARTED or PASSENGER_ONBOARD")

        return route_type
    
    @property
    def driver_info(self) -> DriverInfo:

        phones = [self.driverInfoVo.phone]
        if self.driverInfoVo.phonePassenger:
            phones.append(self.driverInfoVo.phonePassenger)

        return DriverInfo(
            name=self.driverInfoVo.name,
            avatar=self.driverInfoVo.avatar,
            phones=phones,
            auto_brand=self.driverInfoVo.carBrand,
            auto_model=self.driverInfoVo.carType,
            auto_plate=self.driverInfoVo.card,
            auto_color=self.driverInfoVo.color
        )

    @classmethod
    def __get_driven_route(cls, order_id: str, status: CaocaoOrderStatus, cache: SimpleCache[queryDriverPolylineResponseData]) -> DrivenRoute | None:
        
        logger.info(f"Getting driven route of order {order_id}")

        # 1. get route type
        try:
            cls.__get_route_type(order_id, status)
        except DuplicateOrConflict:
            return None

        # 3. get from cache
        res = cache.get()

        # 4. transform to DrivenRoute
        result = []
        for step in res.steps:
            result.extend(step.to_standard())
        
        return DrivenRoute(root=result)

    @property
    def driven_route(self) -> DrivenRoute | None:
        return self.__get_driven_route(self.id, self.inner_status, self._ROUTE_INFO_CACHE)

    @classmethod
    def __get_navigation_info(cls, order_id, cache: SimpleCache[queryDriverPolylineResponseData]) -> NavigationInfo | None:
        
        logger.info(f"Getting navigation info of order {order_id}")

        # 1. get eta info
        try:
            route_info = cache.get()
        except Exception:
            logger.warning(f"Cannot get route info of order {order_id}")
            return None
        else:
            eta_info = route_info.driverEtaInfoVO

            # 2. get driver location
            data = queryDriverLocationRequestData(order_id=order_id)
            res: dict = cls.__base_request('GET', '/common/queryDriverLocationByOrderId', data.model_dump(exclude_unset=True)).data
            driver_location: queryDriverLocationResponseData = queryDriverLocationResponseData(**res)

            # 3. compose result
            return NavigationInfo(
                heading=driver_location.direction,
                lat=driver_location.latitude,
                lng=driver_location.longitude,
                speed=eta_info.speed,
                remain_duration=eta_info.remainTime,
                remain_length=eta_info.remainDistance,
                remain_traffic_lights=eta_info.remainLightCount
            )
    
    @property
    def navigation_info(self) -> NavigationInfo | None:
        return self.__get_navigation_info(self.id, self._ROUTE_INFO_CACHE)

    @property
    def winner(self) -> Competitor:
        
        """
        获取车型胜出者

        多车型下单时，曹操内部会自动进行竞争，只需要通过该接口获取胜出的车型即可
        """
        ride_type = RideTypeManager(
            car_type=self.basicOrderVO.requireLevel,
            service_provider=self._SERVICE_PROVIDER_ID,
            carpool=self.basicOrderVO.carpoolFlag.__bool__(),
            relay=self.basicOrderVO.isRelayOrder,
            league=self.basicOrderVO.cpDriver
        )

        return Competitor(
            ride_type=ride_type.id,
            price_key="",
            type=self.fare_type,
            total=self.orderFeeVo.originTotalFee,
            actual=self.orderFeeVo.totalFee,
            details=[item.to_standard() for item in self.orderFeeVo.detailFeeVos],
            service_provider_order_id=self.id,
        )

    @property
    def fare_type(self) -> RideHailingOrderFareType:

        """
        获得标准的FareType

        需要根据isSpecialFixedPrice与isRouteFixedPrice判断
        """
        if self.basicOrderVO.routeFixedPrice:
            return RideHailingOrderFareType.ROUTE_FIXED
        if self.basicOrderVO.specialFixedPrice:
            return RideHailingOrderFareType.SPECIAL_FIXED
        return RideHailingOrderFareType.COMMON
    
    @property
    def fare(self) -> Tuple[int, List[PriceDetail]]:

        """
        注意该映射不完整，应该还要映射高速路桥费用到费用明细
        """

        return self.orderFeeVo.totalFee, [
            i.to_standard() for i in self.orderFeeVo.detailFeeVos
        ]

    def sync_status(self, order_manager):
        order_manager.status = self.status

    def sync_fare_type(self, order_manager):

        """
        同步计价类型
        """
        order_manager.fare_type = self.fare_type

    def sync_timeline(self, order_manager):

        """
        同步时间线

        有：startServiceTime, beginChargeTime, finishTime, payTime, canceledTime, orderTime, striveTime, arrivedTime
        映射到：start_service, begin_charge, end_service, pay, cancel, 不作映射, accept, drop
        """
        timeline = order_manager.timeline
        if self.basicOrderVO.startServiceTime:
            timeline["start_service"] = get_datetimez(iso8601=self.basicOrderVO.startServiceTime)
        if self.basicOrderVO.beginChargeTime:
            timeline["begin_charge"] = get_datetimez(iso8601=self.basicOrderVO.beginChargeTime)
        if self.basicOrderVO.finishTime:
            timeline["end_service"] = get_datetimez(iso8601=self.basicOrderVO.finishTime)
        if self.basicOrderVO.payTime:
            timeline["pay"] = get_datetimez(iso8601=self.basicOrderVO.payTime)
        if self.basicOrderVO.canceledTime:
            timeline["cancel"] = get_datetimez(iso8601=self.basicOrderVO.canceledTime)
        if self.basicOrderVO.striveTime:
            timeline["accept"] = get_datetimez(iso8601=self.basicOrderVO.striveTime)
        if self.basicOrderVO.arrivedTime:
            timeline["arrive"] = get_datetimez(iso8601=self.basicOrderVO.arrivedTime)
    
    def sync_drive(self, order_manager):

        """
        同步行驶信息
        """
        if self.basicOrderVO.normalTime:
            order_manager.drive.duration = self.basicOrderVO.normalTime
        if self.basicOrderVO.normalDistance:
            order_manager.drive.distance = self.basicOrderVO.normalDistance