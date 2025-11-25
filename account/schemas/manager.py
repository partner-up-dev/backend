import typing
import enum
from blue_firmament.scheme import BaseScheme


class V2WXMPLoginBody(BaseScheme, proxy=False):
    code: str
    """授权码"""


class PIIType(enum.Enum):
    EMAIL = "email"
    PHONE = "phone"


class V1SetPIIVerProvider(enum.Enum):
    """设置PII的Query:VerficationProvider的枚举类型"""

    CODE = "code"
    """系统验证码"""
    WXMP_MP = "wxmp_mp"
    """微信小程序"""


class V1SetPIIBody(BaseScheme, proxy=False):
    code: str
    """验证码
    
    - 系统验证码
    - 微信小程序获取手机号接口的兑换码
    """
