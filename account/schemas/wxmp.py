"""微信公众平台鉴权模块数据模型"""

import enum
from dal import SupabaseAnonPostgrest
from ..schemas.account import AccountRef
from blue_firmament.scheme import BaseScheme, FieldT, field


class WXMPClientType(enum.Enum):
    """微信公众平台客户端类型"""

    MINIPROGRAM = "wxmp_mp"
    """小程序"""
    SERVICE_ACCOUNT = "wxmp_sa"
    """服务号"""


class WXMPAccount(BaseScheme, dal=SupabaseAnonPostgrest, dal_path=("wxmp", "account")):
    """微信公众平台帐号"""

    id: FieldT[AccountRef] = field(is_key=True)
    weixin_mp_openid: FieldT[str | None] = field(default=None)
    """微信小程序OPENID"""
    weixin_sa_openid: FieldT[str | None] = field(default=None)
    """微信服务号OPENID"""
    weixin_unionid: FieldT[str | None] = field(default=None)
    """微信开放平台UNIONID"""

    @classmethod
    def get_openid_field(cls, client_type: WXMPClientType) -> FieldT:
        """获取存储该客户端类型对应OpenID的字段

        :param client_type: 客户端类型
        """
        if client_type == WXMPClientType.MINIPROGRAM:
            return cls.weixin_mp_openid
        elif client_type == WXMPClientType.SERVICE_ACCOUNT:
            return cls.weixin_sa_openid
        else:
            raise ValueError(f"Unsupported OAuth provider {client_type}")

    def set_openid(self, client_type: WXMPClientType, openid: str) -> None:
        openid_field = self.get_openid_field(client_type)
        self[openid_field] = openid
