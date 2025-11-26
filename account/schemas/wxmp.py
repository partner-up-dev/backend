"""微信公众平台鉴权模块数据模型"""

import enum
import sqlmodel
from typing import Optional as Opt
from .account import AccountRef


class WXMPClientType(enum.Enum):
    """微信公众平台客户端类型"""

    MINIPROGRAM = "wxmp_mp"
    """小程序"""
    SERVICE_ACCOUNT = "wxmp_sa"
    """服务号"""


class WXMPAccount(sqlmodel.SQLModel, table=True):
    """微信公众平台帐号"""
    __tablename__ = "wxmp"  # type: ignore
    __table_args__ = {"schema": "account"}

    id: AccountRef = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.String, primary_key=True),
    )
    weixin_mp_openid: Opt[str] = sqlmodel.Field(default=None)
    """微信小程序OPENID"""
    weixin_sa_openid: Opt[str] = sqlmodel.Field(default=None)
    """微信服务号OPENID"""
    weixin_unionid: Opt[str] = sqlmodel.Field(default=None)
    """微信开放平台UNIONID"""

    @classmethod
    def get_openid_field_name(cls, client_type: WXMPClientType) -> str:
        """获取存储该客户端类型对应OpenID的字段名

        :param client_type: 客户端类型
        """
        if client_type == WXMPClientType.MINIPROGRAM:
            return "weixin_mp_openid"
        elif client_type == WXMPClientType.SERVICE_ACCOUNT:
            return "weixin_sa_openid"
        else:
            raise ValueError(f"Unsupported OAuth provider {client_type}")

    def set_openid(self, client_type: WXMPClientType, openid: str) -> None:
        field_name = self.get_openid_field_name(client_type)
        setattr(self, field_name, openid)
