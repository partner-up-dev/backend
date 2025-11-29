"""支付-钱包数据模型
"""

import enum
import datetime
from typing import Optional as Opt
from pydantic import BaseModel
from .base import PaymentPlatform


class WalletIssuer(enum.Enum):
    """钱包发行商
    """
    ALIPAY = "alipay"
    WECHAT = "wechat"
    CCB = "ccb"


class Wallet(BaseModel):
    """钱包
    """

    type: PaymentPlatform
    """钱包类型，也即支付平台"""
    owned_by: str
    """所有者"""
    issuer: WalletIssuer
    """发行商"""
    makeable: bool = True
    """可支付"""
    receivable: bool = True
    """可收款"""
    card_no: Opt[str] = None
    """卡号，按类型需要填写"""
    expired_at: Opt[datetime.datetime] = None
    """有效期"""
    name: Opt[str] = None
    """名称"""
    security_code: Opt[str] = None
    """安全码"""
