"""微信支付数据模型
"""

import datetime
import enum
import typing
from typing import Optional as Opt, Literal as Lit
from ..base import Currency
from .base import PaymentPlatform, TransactionStatus, TransactionType, Transaction
from pydantic import BaseModel


class WechatProductType(enum.Enum):
    PAYMENT = "payment"
    TRANSFER = "transfer"
    REFUND = "refund"


''' Transaction '''

class WechatPaymentType(enum.Enum):
    """微信支付类型
    """
    JSAPI = "JSAPI"
    NATIVE = "NATIVE"  # 扫码支付
    APP = "APP"
    MWEB = "MWEB"  # H5支付
    MICROPAY = "MICROPAY"  # 付款码支付
    FACEPAY = "FACEPAY"  # 刷脸支付

class WechatCollectState(enum.Enum):
    """微信支付收款订单状态
    """
    SUCCESS = "SUCCESS"
    REFUND = "REFUND"
    NOTPAY = "NOTPAY"
    CLOSED = "CLOSED"
    REVOKED = "REVOKED"
    USERPAYING = "USERPAYING"
    PAYERROR = "PAYERROR"

    @staticmethod
    def to_union(trade_state: "WechatCollectState") -> "TransactionStatus":
        """转为统一订单状态
        """
        if trade_state == WechatCollectState.SUCCESS:
            return TransactionStatus.SUCCESS
        elif trade_state == WechatCollectState.REFUND:
            return TransactionStatus.REFUNDED
        elif trade_state == WechatCollectState.NOTPAY:
            return TransactionStatus.NOT_PAID
        elif trade_state == WechatCollectState.CLOSED:
            return TransactionStatus.CANCELLED
        elif trade_state == WechatCollectState.REVOKED:
            return TransactionStatus.REVOKED
        elif trade_state == WechatCollectState.USERPAYING:
            return TransactionStatus.IN_PROGRESS
        elif trade_state == WechatCollectState.PAYERROR:
            return TransactionStatus.ERROR
        else:
            raise ValueError("Invalid trade state")

class WechatPaymentAmount(BaseModel):

    total: int
    currency: Currency
    payer_total: int
    payer_currency: Currency

class WechatCollectTransaction(BaseModel):

    """微信支付收款订单
    """

    appid: str
    mchid: str
    out_trade_no: str
    transaction_id: str
    trade_type: WechatPaymentType
    trade_state: WechatCollectState
    trade_state_desc: str
    bank_type: str
    attach: str
    success_time: str
    payer: typing.Dict[Lit["openid"], str]
    amount: WechatPaymentAmount
    scene_info: Opt[typing.Dict[str, str]] = None
    promotion_detail: Opt[list] = None

    def to_union(self) -> Transaction:
        return Transaction(
            id=self.out_trade_no,
            platform_id=self.transaction_id,
            type=TransactionType.COLLECT,
            platform=PaymentPlatform.WECHAT,
            amount=self.amount.total,
            currency=self.amount.currency,
            successed_at=datetime.datetime.fromisoformat(self.success_time),
            status=WechatCollectState.to_union(
                self.trade_state
            ),
        )


class WechatPaymentTransferStatus(enum.Enum):
    """微信支付转账订单状态
    """
    WAIT_PAY = "WAIT_PAY"
    ACCEPTED = "ACCEPTED"
    PROCESSING = "PROCESSING"
    FINISHED = "FINISHED"
    CLOSED = "CLOSED"

    def to_union(self) -> TransactionStatus:

        """
        将微信支付转账状态转换为统一交易状态
        """
        if self is WechatPaymentTransferStatus.FINISHED:
            return TransactionStatus.SUCCESS
        elif self is WechatPaymentTransferStatus.CLOSED:
            return TransactionStatus.CANCELLED
        else:
            return TransactionStatus.IN_PROGRESS 

class WechatPaymentTransferTransaction(BaseModel):

    """微信支付转账订单
    """
    out_batch_no: str
    batch_id: str
    batch_status: WechatPaymentTransferStatus
    total_num: int
    total_amount: int
    success_amount: int
    success_num: int
    fail_amount: int
    fail_num: int
    update_time: str

    def to_union(self) -> Transaction:
        """
        有损转换！
        - status: 如果fail_num不为0，那么status为ERROR
        - amount: 无法得知total_amount
        - paid_at: 使用update_time
        """

        status = WechatPaymentTransferStatus.to_union(self.batch_status)
        if self.fail_num != 0:
            status = TransactionStatus.ERROR

        return Transaction(
            id=self.out_batch_no, 
            platform_id=self.batch_id,
            platform=PaymentPlatform.WECHAT, 
            type=TransactionType.TRANSFER,
            amount=self.success_amount,
            currency=Currency.CNY, 
            successed_at=datetime.datetime.fromisoformat(self.update_time),
            status=status
        )
    

class WechatPaymentRefundStatus(enum.Enum):
    """微信支付退款状态
    """
    SUCCESS = "SUCCESS"
    CLOSED = "CLOSED"
    PROCESSING = "PROCESSING"
    ABNORMAL = "ABNORMAL"

    def to_union(self) -> TransactionStatus:
        if self is WechatPaymentRefundStatus.SUCCESS:
            return TransactionStatus.SUCCESS
        elif self is WechatPaymentRefundStatus.CLOSED:
            return TransactionStatus.CANCELLED
        elif self is WechatPaymentRefundStatus.ABNORMAL:
            return TransactionStatus.ERROR
        elif self is WechatPaymentRefundStatus.PROCESSING:
            return TransactionStatus.IN_PROGRESS
        raise ValueError("unknown status")


class WechatPaymentRefundTransaction(BaseModel):
    """微信支付退款订单
    """
    mchid: str
    out_trade_no: str
    transaction_id: str
    out_refund_no: str
    refund_id: str
    refund_staus: WechatPaymentRefundStatus
    success_time: Opt[datetime.datetime] = None
    user_received_account: str
    amount: int

    def to_union(self) -> Transaction:
        return Transaction(
            id=self.out_refund_no,
            platform_id=self.refund_id,
            type=TransactionType.REFUND,
            platform=PaymentPlatform.WECHAT,
            currency=Currency.CNY,
            successed_at=self.success_time,
            status=self.refund_staus.to_union(),
            amount=self.amount
        )


''' Callback '''
class CallbackEventType(enum.Enum):
    TRANSACTION_SUCCESS = "TRANSACTION.SUCCESS"

class CallbackResouceType(enum.Enum):
    ENCRYPT_RESOUCE = "encrypt-resouce"

class CallbackResouceAlgorithm(enum.Enum):
    AEAD_AES_256__GCM = "AEAD_AES_256_GCM"

class CallbackResourceOriginalType(enum.Enum):
    TRANSACTION = "transaction"

class Resource(BaseModel):
    algorithm: CallbackResouceAlgorithm
    associated_data: str
    ciphertext: str
    nonce: str
    original_type: CallbackResourceOriginalType

class WechatPaymentCallbackBody(BaseModel):

    create_time: datetime.datetime
    event_type: CallbackEventType
    id: str
    resouce_type: CallbackResouceType
    resource: Resource
    summary: str
