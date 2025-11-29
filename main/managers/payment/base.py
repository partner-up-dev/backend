"""支付管理器基础

Business logic for payment operations using FastAPI patterns.

:author: Lan_zhijiang<lanzhijiang@hadream.ltd>
"""

__all__ = ["PAYMENT_GATEWAY", "BasePaymentManager"]

import abc
import datetime
import typing
from typing import Optional as Opt

from account.schemas import AccountRef
from ...schemas.base import Currency
from ...schemas.payment.base import PaymentPlatform, Transaction

PAYMENT_GATEWAY: typing.Dict[PaymentPlatform, type["BasePaymentManager"]] = {}
"""支付平台与支付平台实现类的注册表

通过该类获得对应支付平台的实现类

Examples
--------
>>> PAYMENT_GATEWAY[PaymentPlatform.WECHAT]
A subclass of BasePaymentManager
"""


class BasePaymentManager(abc.ABC):
    """支付管理器基类

    - 所有金额为整型，以分为单位
    - 子类是特定支付平台的实现
    - 子类实例服务一类客户端发起的对其平台的支付操作
    - 通过该基类获得某平台服务于某客户端的实例

    Examples
    --------
    >>> BasePaymentManager['client_id_xxxx'].collect
    """

    __platform__: PaymentPlatform
    """支付平台类型"""
    __id__: str
    """唯一标识，用于唯一地找到该类"""
    __registry__: typing.List[tuple[tuple[str, ...], typing.Type[typing.Self]]]
    """服务客户端具体支付管理类与所服务的客户端的注册表"""

    def __init_subclass__(
        cls,
        platform: Opt[PaymentPlatform] = None,
        _id: Opt[str] = None,
        client_ids: Opt[tuple[str, ...]] = None,
        **kwargs,
    ) -> None:
        """

        :param _id: 唯一标识，用于唯一地找到该类
        :param client_ids: 服务的客户端 ID（可为多个）
        :type client_ids: Opt[tuple[str, ...]]
        """
        if platform:
            cls.__platform__ = platform
            PAYMENT_GATEWAY[platform] = cls
        if not hasattr(cls, "__registry__"):
            cls.__registry__ = []
        if _id:
            cls.__id__ = _id
        if client_ids:
            cls.__registry__.append((client_ids, cls))

        return super().__init_subclass__(**kwargs)

    @classmethod
    def get(cls, client_id: Opt[str] = None) -> typing.Self:
        """Get payment manager instance for a client.

        :param client_id: 客户端 ID
        :type client_id: str
        :raises TypeError: 没有可以服务该客户端的支付管理器
        :return: 支付管理器实例
        """
        for i in cls.__registry__:
            if client_id in i[0]:
                return i[1]()
        raise TypeError(
            f"No payment manager for client {client_id} was found in {cls.__platform__}"
        )

    @classmethod
    def get_by_id(cls, _id: Opt[str]) -> typing.Self:
        """通过ID获取支付管理器

        :param _id: 支付管理器ID（None 则选择第一个）
        :type _id: Opt[str]
        :raises KeyError: 没有该 ID 的支付管理器
        :return: 支付管理器实例
        """
        if _id is None:
            return cls.__registry__[0][1]()
        for i in cls.__registry__:
            if _id == i[1].__id__:
                return i[1]()
        raise KeyError("No such payment manager")

    @property
    @abc.abstractmethod
    def _id(self) -> str: ...

    @abc.abstractmethod
    def get_fee(self, amount: int) -> int:
        """计算手续费"""

    @abc.abstractmethod
    def collect(
        self,
        *,
        _id: str,
        amount: int,
        payer: AccountRef,
        currency: Currency = Currency.CNY,
        description: str = "",
        expired_at: Opt[datetime.datetime] = None,
        callback_url: Opt[str] = None,
        client_id: Opt[str] = None,
        **kwargs,
    ) -> dict:
        """收款

        支付平台将会创建支付订单并返回预支付 ID，客户端使用该 ID 请求用户
        完成支付。

        :param _id: 内部自定义ID
        :param amount: 收款金额 int
        :param payer: 付款人
        :param currency: 货币
        :param description:
        :param expired_at: 支付截止时间
        :param callback_url: 支付结果回调地址

        :returns:
        """

    @abc.abstractmethod
    def refund(
        self,
        *,
        _id: str,
        collect_id: str,
        amount: int,
        currency: Currency = Currency.CNY,
        callback_url: Opt[str] = None,
        reason: Opt[str] = None,
        **kwargs,
    ) -> Transaction:
        """退款

        :param _id: 退款订单ID
        :param collect_id: 支付订单ID
        :param amount: 退款金额，不可以大于支付金额
        """

    @abc.abstractmethod
    def transfer(
        self,
        *,
        _id: str,
        amount: int,
        payee: AccountRef,
        remark: Opt[str] = None,
        currency: Currency = Currency.CNY,
        callback_url: Opt[str] = None,
        **kwargs,
    ) -> str:
        """转账

        :param payee: 收款账号
        :param remark: 转账备注
        :returns: 客户端用于拉起用户确认的信息
        """

    @abc.abstractmethod
    def get_collect_transaction(self, _id: str) -> Transaction:
        """获取收款订单"""

    @abc.abstractmethod
    def get_signature(self, app_id: str, prepay_id: str, sign_type: Opt[str] = None) -> dict:
        """获取前端用于调起支付的签名"""

    @abc.abstractmethod
    def resolve_collect_callback(self, data: dict) -> Transaction:
        """解析收款回调通知"""

    @abc.abstractmethod
    def resolve_transfer_callback(self, data: dict) -> Transaction:
        """解析转账回调通知"""

    @abc.abstractmethod
    def resolve_refund_callback(self, data: dict) -> Transaction:
        """解析退款回调通知"""
