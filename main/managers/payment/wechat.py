"""
author: Lan_zhijiang
date: 2024-09-15
desc: 微信支付
issues:
    #63

Refactored to remove BlueFirmament dependencies.
"""

__module_name__ = "WechatPayment"

# typing
import datetime
import random
import string
import typing
import structlog
from typing import Optional as Opt, Literal as Lit
from fastapi import HTTPException
from .base import BasePaymentManager
from ...schemas.base import Currency
from ...schemas.payment.wechat import (
    WechatCollectTransaction,
    WechatPaymentRefundTransaction,
    WechatPaymentTransferTransaction,
)

# libs
from wechatpayv3 import WeChatPay as WechatPayClient, WeChatPayType as PayType, SignType

# utils
import json
import re
from account.schemas import AccountRef
from ...schemas.payment.base import (
    PaymentPlatform,
    TransactionStatus,
    TransactionType,
    Transaction,
    TransferScene,
)

# setting
from settings.wechat_pay import get_setting

logger = structlog.get_logger("WechatPayment")


def get_datetimez(timezone=None):
    """Get current datetime with timezone."""
    if timezone:
        return datetime.datetime.now(timezone)
    return datetime.datetime.now(datetime.timezone.utc)


class WechatPaymentException(HTTPException):
    """
    微信支付平台异常对象

    Docs
    ----
    https://pay.weixin.qq.com/docs/merchant/development/interface-rules/basic-rules.html
    """

    def __init__(self, message: str, **kwargs) -> None:
        res = json.loads(message)
        self.code = res.get("code", None)
        errmsg = res.get("message", None)
        self.detail = res.get("detail", None)

        super().__init__(status_code=500, detail=errmsg)


class WechatPaymentManager(
    BasePaymentManager,
    manager_name="wechatpay",
    platform=PaymentPlatform.WECHAT,
):
    """微信支付管理器"""

    def get_fee(self, amount: int) -> int:
        return int(amount * 0.006)

    __client__: WechatPayClient

    def __init_subclass__(
        cls,
        client_id: str,
        appid: str,
        paytype: PayType,
        mchid: str,
        serial_no: str,
        pri_key_path: str,
        api_v3_key: str,
        cert_dir: str,
        **kwargs,
    ) -> None:
        """

        :param client_id: 服务的客户端的ID
        :type client_id: str
        :param appid: 该客户端在微信支付平台的 APPID
        :type appid: str
        :param paytype: 支付类型，如 JSAPI, NATIVE
        :type paytype: PayType
        :param mchid: 商户ID
        :type mchid: str
        :param serial_no: 商家证书序列号
        :type serial_no: str
        :param pri_key_path: 商家证书私钥文件位置
        :type pri_key: str
        :param api_v3_key: V3 版本的 API 密钥
        :type api_v3_key: str
        :param cert_dir: 证书存放的文件夹
        :type cert_dir: str
        """
        with open(pri_key_path, "r") as f:
            pri_key = f.read()
        cls.__client__ = WechatPayClient(
            wechatpay_type=paytype,
            appid=appid,
            mchid=mchid,
            cert_serial_no=serial_no,
            private_key=pri_key,
            apiv3_key=api_v3_key,
            cert_dir=cert_dir,
            logger=logger,
        )

        super().__init_subclass__(_id=mchid, client_ids=(client_id,), **kwargs)

    @property
    def _client(self) -> WechatPayClient:
        return self.__client__

    @property
    def _id(self) -> str:
        return self._client._mchid

    @classmethod
    def _validate_id(cls, _id: str) -> None:
        if not (6 <= len(_id) <= 32):
            raise HTTPException(status_code=400, detail=f"id length should be 6~32: {_id}")
        if not re.match(r"^[0-9A-Za-z_\-\|\*]+$", _id):
            raise HTTPException(status_code=400, detail=f"invalid id: {_id}")

    def resolve_res(self, http_status_code: int, res_text: str) -> dict:
        """处理微信支付接口的返回

        Parameters
        ----------
        http_status_code : (HTTP)状态码
        message : 消息

        Description
        -----------
        如果状态码异常，会触发一定的预设操作并抛出WechatPaymentException

        Returns
        -------
        dict
            JSON序列化的消息
        """
        res = json.loads(res_text)
        if http_status_code == 200:
            return res
        else:
            code = res["code"]
            if code == "APPID_MCHID_NOT_MATCH":
                raise HTTPException(
                    status_code=400,
                    detail=f"client not served by this mch: {self._client._appid}"
                )
            elif code == "OUT_TRADE_NO_USED":
                raise HTTPException(status_code=400, detail="_id duplicated")
            elif code == "OPENID_MISMATCH":
                raise HTTPException(
                    status_code=400,
                    detail=f"openid not match the appid: {self._client._appid}"
                )
            elif code == "NOT_ENOUGH":
                # TODO 商户余额不足
                pass
            elif code == "RESOURCE_NOT_EXISTS":
                # TODO 退款时支付订单未支付
                pass
            elif code == "USER_ACCOUNT_ABNORMAL":
                # TODO 用户账号异常，商户可以自定处理退款
                pass
            elif code == "ORDER_NOT_EXIST":
                raise HTTPException(status_code=404, detail="transaction not exist")

            raise HTTPException(status_code=500, detail="wechat_pay error")

    def _get_openid(self, account_id: AccountRef) -> str:
        """获取该用户在该 APPID 中的 OPENID"""
        # TODO remove me
        return "oK1ud62mEB8g96ov_PYz_Ye2YRws"
        # else:
        #     return AccountManager.get_wxmp_openid(account_id)

    @staticmethod
    def _to_transacation_status(wechat_pay_status: str) -> TransactionStatus:
        if wechat_pay_status == "SUCCESS":
            return TransactionStatus.SUCCESS
        elif wechat_pay_status == "NOTPAY":
            return TransactionStatus.NOT_PAID
        elif wechat_pay_status == "CLOSED":
            return TransactionStatus.CANCELLED
        elif wechat_pay_status == "PROCESSING":
            return TransactionStatus.IN_PROGRESS
        elif wechat_pay_status == "REFUND":
            return TransactionStatus.REFUNDED
        elif wechat_pay_status == "REVOKED":
            return TransactionStatus.REVOKED
        elif wechat_pay_status == "USERPAYING":
            return TransactionStatus.IN_PROGRESS
        elif wechat_pay_status == "PAYERROR":
            return TransactionStatus.ERROR
        elif wechat_pay_status == "ABNORMAL":
            return TransactionStatus.ERROR
        raise ValueError(f"unknown status {wechat_pay_status}")

    def collect(
        self,
        *,
        _id: str,
        amount: int,
        description: str = "",
        payer: AccountRef,
        currency: Currency = Currency.CNY,
        expired_at: Opt[datetime.datetime] = None,
        callback_url: Opt[str] = None,
        client_id: Opt[str] = None,
        **attachments,
    ) -> dict:
        """收款

        :param _id: 即out_trade_no，商户内部订单ID

            6-32个字符，只能是数字、大小写字母_-|*
        :param amount: 收款金额
        :param description: 订单描述，长度限制为127
        :param payer: 付款用户 ID

            通过账号管理器获得该用户在该客户端的 OPENID
        :param expired_at: 支付截止时间

            - 不可以早于现在之后的一分钟
            - TODO 需要添加倒计时任务，微信支付只会在 7 天后关单；
            time_expire 只会阻止用户支付，不会关单
        :param callback_url: 支付结果回调URL

            不可以携带参数，长度限制为255
        :param attachments: 附加信息，序列化为 JSON 后长度在 127 内
        :returns: 预支付ID
        :rtype: str

        `微信支付文档 <https://pay.weixin.qq.com/docs/merchant/apis/mini-program-payment/mini-prepay.html>`_
        """
        self._validate_id(_id)

        attachment_str = json.dumps(attachments)[0:128] if attachments else None
        amount_obj = {"total": amount, "currency": currency.value}
        payer_obj = (
            {
                "openid": self._get_openid(payer)  # TODO
            }
            if self._client._type not in (PayType.NATIVE,)
            else None
        )

        # 2. request
        code, message = self._client.pay(
            description=description[0:127],
            out_trade_no=_id,
            amount=amount_obj,
            payer=payer_obj,
            time_expire=None if not expired_at else expired_at.isoformat(),
            attach=attachment_str,
            notify_url=None if not callback_url else callback_url[0:255],
            appid=client_id,
        )

        res = self.resolve_res(code, message)
        if self._client._type in (PayType.JSAPI, PayType.APP):
            # TODO add time_stamp, nonce_str ... pay_sign
            return res
        elif self._client._type == PayType.NATIVE:
            return {
                "url": res["code_url"],
            }
        elif self._client._type == PayType.H5:
            return {
                "url": res["h5_url"],
            }

        raise NotImplementedError(f"{self._client._type} not supported yet")

    def get_collect_transaction(self, id: str) -> Transaction:
        """通过商户内部订单ID获取收款订单"""
        code, message = self._client.query(out_trade_no=id)

        res = self.resolve_res(code, message)
        return Transaction(
            id=res["out_trade_no"],
            platform_id=res.get("transaction_id", ""),
            type=TransactionType.PAYMENT,
            platform=self.__platform__,
            amount=res["amount"]["total"],
            currency=Currency(res["amount"]["currency"]),
            successed_at=res.get("success_time", None),
            status=self._to_transacation_status(res["trade_state"]),
        )

    def _decrypt_callback(self, data: dict, headers: dict) -> dict:
        """Verify and decrypt WeChat callback notification content.

        :param data: Callback request body as dictionary
        :param headers: HTTP headers from the callback request
        :return: Decrypted resource content
        :raises HTTPException: If callback verification fails
        """
        wechat_headers = {
            "Wechatpay-Signature": headers.get("wechatpay-signature", ""),
            "Wechatpay-Timestamp": headers.get("wechatpay-timestamp", ""),
            "Wechatpay-Nonce": headers.get("wechatpay-nonce", ""),
            "Wechatpay-Serial": headers.get("wechatpay-serial", ""),
        }
        result = self._client.callback(wechat_headers, json.dumps(data))
        if result:
            return result["resource"]
        else:
            raise HTTPException(status_code=400, detail="invalid callback")

    def resolve_collect_callback(self, data: dict, headers: dict = None) -> Transaction:
        """Verify and decrypt payment callback notification.

        :param data: Callback request body
        :param headers: HTTP headers from callback request
        :return: Parsed transaction

        `WeChat Docs <https://pay.weixin.qq.com/docs/merchant/apis/mini-program-payment/payment-notice.html>`_
        """
        headers = headers or {}
        result = self._decrypt_callback(data, headers)
        return WechatCollectTransaction(**result).to_union()

    def resolve_transfer_callback(self, data: dict, headers: dict = None) -> Transaction:
        """Verify and decrypt transfer callback notification.

        :param data: Callback request body
        :param headers: HTTP headers from callback request
        :return: Parsed transaction

        `WeChat Docs <https://pay.weixin.qq.com/docs/merchant/apis/batch-transfer-to-balance/transfer-batch-callback-notice.html>`_
        """
        headers = headers or {}
        result = self._decrypt_callback(data, headers)
        return WechatPaymentTransferTransaction(**result).to_union()

    def resolve_refund_callback(self, data: dict, headers: dict = None) -> Transaction:
        """Verify and decrypt refund callback notification.

        :param data: Callback request body
        :param headers: HTTP headers from callback request
        :return: Parsed transaction

        `WeChat Docs <https://pay.weixin.qq.com/doc/v3/merchant/4013071196>`_
        """
        headers = headers or {}
        result = self._decrypt_callback(data, headers)
        return WechatPaymentRefundTransaction(**result).to_union()

    @staticmethod
    def _to_transfer_scene_id(scene: TransferScene) -> int:
        if scene == TransferScene.SPLIT_BILL:
            return 1009
        raise ValueError(f"unsupported transfer scene {scene}")

    def transfer(
        self,
        *,
        _id: str,
        amount: int,
        payee: AccountRef,
        remark: Opt[str] = None,
        currency: Currency = Currency.CNY,
        callback_url: Opt[str] = None,
        client_id: Opt[str] = None,
        scene: TransferScene,
        report_infos: typing.List[dict[Lit["info_type"] | Lit["info_content"], str]],
        **kwargs,
    ) -> str:
        """转账

        :param _id: 商户内部转账订单ID
        :param remark: 转账备注 32字符
        :param scene: 转账场景
        :param report_infos: 转账报备信息，不同场景有不同的要求

        `微信支付文档 <https://pay.weixin.qq.com/docs/merchant/apis/batch-transfer-to-balance/transfer-batch/initiate-batch-transfer.html>`_
        """
        self._validate_id(_id)

        if amount >= 200000:
            # TODO support realname
            raise NotImplementedError("amount >= 2000, realname required")

        code, message = self._client.mch_transfer_bills(
            out_bill_no=_id,
            transfer_remark=remark if not remark else remark[0:32],
            transfer_amount=amount,
            openid=self._get_openid(payee),
            transfer_scene_id=str(self._to_transfer_scene_id(scene)),
            transfer_scene_report_infos=report_infos,
            notify_url=callback_url,
            appid=client_id,
        )

        res = self.resolve_res(code, message)
        return res["package_info"]

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

        Parameters
        ----------
        :param _id: 商户内部退款订单ID
        :param collect_id: 商户内部支付订单ID
        :param reason: 退款原因，80 字符内
        """
        self._validate_id(_id)

        collect_trans = self.get_collect_transaction(collect_id)
        amount_obj = {
            "refund": amount,
            "total": collect_trans.amount,
            "currency": currency.value,
        }
        reason_str = reason[0:80] if reason else None

        # 2. request
        code, message = self._client.refund(
            out_refund_no=_id,
            out_trade_no=collect_id,
            amount=amount_obj,
            reason=reason_str,
            notify_url=callback_url,
        )

        res = self.resolve_res(code, message)
        return Transaction(
            id=res["refund_id"],
            platform_id=res["out_refund_no"],
            type=TransactionType.REFUND,
            platform=self.__platform__,
            amount=res["amount"]["payer_refund"],
            currency=currency,
            successed_at=res.get("success_time", None),
            status=self._to_transacation_status(res["status"]),
        )

    def get_signature(self, app_id: str, prepay_id: str, sign_type: Opt[str] = None) -> dict:
        """获取调起支付的签名

        :param sign_type: 签名类型，目前仅支持 RSA
        """
        time_stamp = str(
            int(
                get_datetimez(
                    timezone=datetime.timezone(offset=datetime.timedelta(hours=8))
                ).timestamp()
            )
        )
        nonce_str = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        packages = f"prepay_id={prepay_id}"
        sign_body = [app_id, time_stamp, nonce_str, packages]

        signature = self._client.sign(data=sign_body, sign_type=SignType.RSA_SHA256)

        return {
            "time_stamp": time_stamp,
            "nonce_str": nonce_str,
            "pay_sign": signature,
        }


class WechatMPPaymentManager(
    WechatPaymentManager,
    client_id="mp_weixin",
    appid="wx7674f72ff1eb49e6",
    paytype=PayType.JSAPI,
    mchid=get_setting().mchid,
    serial_no=get_setting().serial_no,
    pri_key_path=get_setting().pri_key_path,
    api_v3_key=get_setting().api_v3_key,
    cert_dir=get_setting().cert_dir,
    manager_name="WechatMPPayment",
):
    """微信小程序支付管理器"""


class WechatWebPaymentManager(
    WechatPaymentManager,
    client_id="web",
    appid="wx7674f72ff1eb49e6",
    paytype=PayType.NATIVE,
    mchid=get_setting().mchid,
    serial_no=get_setting().serial_no,
    pri_key_path=get_setting().pri_key_path,
    api_v3_key=get_setting().api_v3_key,
    cert_dir=get_setting().cert_dir,
    manager_name="WechatWebPayment",
):
    """微信小程序支付管理器（Web 模式）"""
