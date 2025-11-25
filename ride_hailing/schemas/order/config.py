"""
author: Lan_zhijiang
date: 2024-09-23
desc: 网约车订单 打车配置 相关数据模型
issues: 
    #7
references: 

"""

__module_name__ = "RideHailingConfigSchema"

# schemas
from enum import Enum
from backend_common.libs.i18n import TranslatableEnum
from backend_common.schemas import BaseSchema, BaseCommonSchema
from backend_common.schemas.serializers import enum_serializer
from app.schemas.service_provider import ServiceProvider

# utils
from app.utils.encryption import Encryption

# libs
from app.libs.exceptions import NotFound

# typing
from pydantic import Field, field_serializer, model_validator, field_validator
from typing import Annotated, List, Union


class CarType(TranslatableEnum):

    """
    汽车类型（服务类型）

    每个平台都有独立的车型，应该继承该枚举
    """
    
    @classmethod
    def from_str_or_int(cls, value: Union[str, int]) -> 'CarType':

        """
        处理输入可能是字符串或整型的情况，每个子类自行实现
        """
        raise NotImplementedError()

class RideType(BaseSchema[str]):

    """
    车型

    https://app.apifox.com/link/project/5303644/apis/schema-125225106
    """
    _ID_TYPE = "hash"

    car_type: CarType
    service_provider: Annotated[ServiceProvider, enum_serializer]
    carpool: bool = False  # 是否拼车
    relay: bool = True  # 是否接力
    league: bool = True  # 是否加盟运力

    @model_validator(mode='before')
    def validate_car_type(cls, values: dict):

        """
        处理车型

        如果不是CarType，则尝试使用ServiceProvider对应的CarType枚举转换该值
        """
        if not isinstance(values.get("car_type"), CarType):
            from app.schemas.union.car_type import get_car_type
            service_provider = values.get("service_provider")
            try:
                values["car_type"] = get_car_type(service_provider).from_str_or_int(
                    values["car_type"]
                )
            except NotFound:
                raise ValueError(f"Car type not available in service_provider {service_provider}")

        return values

    @field_serializer("car_type")
    def car_type_serializer(self, value: CarType):
        return str(value.value)


class RideTypeForDisplay(BaseSchema):

    """
    车型（展示用途）
    """
    service_provider: str
    """翻译后的服务提供商"""
    car_type: str
    """翻译后的车型（基于服务提供商）"""

    def __str__(self):
        return f"{self.service_provider} {self.car_type}"

class Purpose(Enum):

    """
    出行目的
    """
    AIRPORT_PICKUP = "airport_pickup"  # 接机
    AIRPORT_DROPOFF = "airport_dropoff"  # 送机
    RAILWAY_PICKUP = "railway_pickup"  # 接站
    RAILWAY_DROPOFF = "railway_dropoff"  # 送站
    COMMON = "common"  # 普通出行
    COMMUTE = "commute"  # 通勤
    SELF_DRIVE = "self_drive"  # 自驾

RideTypes = List[RideType]
'''车型偏好，顺序即权重'''

class RideHailingPreference(BaseCommonSchema):

    """
    打车偏好

    https://app.apifox.com/link/project/5303644/apis/schema-125221956
    """
    ride_types: RideTypes = Field(default_factory=list)
    purpose: Annotated[Purpose | None, enum_serializer]
    luggage: int | None = None  # 行李升
    flight: str | None = None  # 航班信息
    railway: str | None = None  # 列车信息
    rental_duration: int | None = Field(default=None, min=1)
    '''租车时长, h'''

    @model_validator(mode='after')
    def validate_rental_duration(cls, values):

        """
        校验租车时长

        如果类型为自驾，则必须填写租车时长
        """
        if values.purpose == Purpose.SELF_DRIVE:
            if not values.rental_duration:
                # Non or 0
                raise ValueError("Rental duration is required for self-drive purpose")
        return values
            
    @model_validator(mode="after")
    def validate_flight(cls, values):

        """
        校验航班信息

        如果类型为接机/送机，则必须填写航班信息
        """
        if values.purpose in [Purpose.AIRPORT_PICKUP, Purpose.AIRPORT_DROPOFF]:
            if not values.flight:
                raise ValueError("Flight information is required for airport purpose")
        return values
            
    @model_validator(mode="after")
    def validate_railway(cls, values):

        """
        校验列车信息

        如果类型为接站/送站，则必须填写列车信息
        """
        if values.purpose in [Purpose.RAILWAY_PICKUP, Purpose.RAILWAY_DROPOFF]:
            if not values.railway:
                raise ValueError("Railway information is required for railway purpose")
        return values
