"""支付-钱包数据模型
"""

import enum
import datetime
import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
from blue_firmament.scheme import (
    BaseScheme, FieldT, field
)
from .base import PaymentPlatform


class WalletIssuer(enum.Enum):
    """钱包发行商
    """
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CCB = "ccb"


class Wallet(BaseScheme):
    """钱包
    """

    __schema_name__ = "payment"
    __table_name__ = "wallet"

    type: PaymentPlatform
    """钱包类型，也即支付平台"""
    owned_by: FieldT[str]
    """所有者"""
    issuer: WalletIssuer
    """发行商"""
    makeable: FieldT[bool] = field(default=True)
    """可支付"""
    receivable: FieldT[bool] = field(default=True)
    """可收款"""
    card_no: Opt[str] = None
    """卡号，按类型需要填写"""
    expired_at: Opt[datetime.datetime] = None
    """有效期"""
    name: Opt[str] = None
    """名称"""
    security_code: Opt[str] = None
    """安全码"""
