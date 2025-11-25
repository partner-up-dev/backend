
__all__ = [
    "Transaction",
    "TransactionStatus",
    "TransactionType",
    "TransferScene",
    "PaymentPlatform"
]

import datetime
import enum
from typing import Optional as Opt
from blue_firmament.scheme import BaseScheme
from ..base import Currency


class PaymentPlatform(enum.Enum):
    WECHAT = "wechat"


class TransactionStatus(enum.Enum):
    SUCCESS = "success"
    REFUNDED = "refunded"
    NOT_PAID = "not_paid"
    CANCELLED = "cancelled"
    REVOKED = "revoked" # TODO 和cancel有啥区别呢？
    IN_PROGRESS = "in_progress"
    ERROR = "error"


class TransactionType(enum.Enum):
    COLLECT = "collect"
    """收款"""
    REFUND = "refund"
    """退款"""
    TRANSFER = "transfer"
    """转账"""


class Transaction(BaseScheme):

    id: str
    type: TransactionType = TransactionType.COLLECT
    platform_id: str
    platform: PaymentPlatform
    amount: int
    currency: Currency
    successed_at: Opt[datetime.datetime] = None
    status: TransactionStatus

    def is_success(self) -> bool:
        return self.status in (TransactionStatus.SUCCESS,)
    def is_failed(self) -> bool:
        return self.status in (TransactionStatus.ERROR,)


class TransferScene(enum.Enum):
    """转账场景"""

    SPLIT_BILL = "split_bill"
    """分账账单转移支付"""
