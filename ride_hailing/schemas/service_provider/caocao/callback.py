"""
author: Lan_zhijiang
date: 2024-11-01
desc: 曹操出行的回调通知相关数据模型
issues: 
    #2
references: 

"""

# typing
from typing import List
from pydantic import BaseModel
from enum import IntEnum

# typing - business module
from app.schemas.service_provider.caocao import CaocaoOrderStatus


class CaocaoCallbackEvent(IntEnum):

    """
    曹操出行通知回调事件

    https://app.apifox.com/link/project/5283937/apis/schema-125623043
    """
    DRIVER_ACCEPT_ORDER = 1
    """预约单对应订单状态2 实时单对应状态9"""
    DRIVER_START_SERVICE = 2
    """出发接乘客,对应订单状态9；仅有预约单、接送机单会有这个事件"""
    DRIVER_ARRIVED = 3
    """对应订单状态12"""
    DRIVER_START_BILLING = 4
    """对应订单状态3"""
    DRIVER_END_BILLING = 5
    """对应订单状态8；（目前没有发送这个事件）"""
    DRIVER_INPUT_EXTRA_FEE = 6
    """结束服务"""
    USER_COMPLAINT = 9
    """无"""
    USER_PAYMENT = 11
    """对应订单状态7"""
    USER_REVIEW = 12
    """对应订单状态6；订单完成评价时触发回调，订单支付后24小时内可调用评价接口，24小时后系统默认好评"""
    CASH_PAYMENT = 13
    """对应订单状态7；默认不配置现金支付，若需配置，请先联系商务"""
    CUSTOMER_SERVICE_CANCEL = 20
    """对应订单状态21；司机接单后到订单支付前客服可以取消订单"""
    USER_CANCEL = 21
    """开始计费前用户可以取消订单：免费取消对应订单状态20用户取消；需支付取消费对应订单状态10订单取消，待付款"""
    SYSTEM_CANCEL = 22
    """无司机接单，超时时间为120s（异常场景下在司机接单后会返回系统取消事件）"""
    PAID_ORDER_PRICE_REDUCTION = 23
    """无"""
    CUSTOMER_SERVICE_PRICE_CHANGE = 24
    """退款之外的改价场景：①已支付订单，改价改高；②未支付订单，改价改低；③未支付订单，改价改高"""
    CUSTOMER_SERVICE_FREE_ORDER = 25
    """订单价格改为0,订单已支付状态客服可以免单"""
    DRIVER_CANCEL = 26
    """对应订单状态26，司机在到达上车点后，且超过最大等待时间后，可以取消乘客订单（需开通此功能请联系商务）免费取消对应订单状态26司机取消；需支付取消费对应订单状态10订单取消，待付款"""
    THIRD_PARTY_CANCEL = 27
    """对应订单状态27，聚合叫车场景，由聚合平台发起"""
    DRIVER_INITIATE_REASSIGN = 40
    """对应订单状态11，仅预约单有此状态（若接入方下单接口选择曹操短信不发送，须注意改派失败的通知）"""
    DRIVER_REASSIGN_FAILED = 41
    """仅预约单有此状态，司机端发起改派后，若5分钟内无其他司机接单则改派失败，改派失败则订单取消"""
    DRIVER_REASSIGN_SUCCESS = 42
    """仅预约单有此状态，改派后接入方调订单详情查询接口更新司机车辆信息，若接入方不处理该流程产生客诉由第三方承担"""
    INVOICE_VOID = 43
    """纸质发票或电子发票作废后，可重新调用发票接口获取，发票作废回调包含：orderNos list 订单id"""
    USER_PAY_CANCEL_FEE = 44
    """对应订单状态13订单取消，已支付"""
    CUSTOMER_SERVICE_EXEMPTION = 45
    """客服对含取消费订单操作免责。未支付取消费订单：客服免责取消后对应订单状态20用户取消或26司机取消；已支付取消费订单：客服免责取消后对应订单状态14免责取消"""
    RELAY_ORDER_PREVIOUS_PASSENGER_CHANGE_DESTINATION = 46
    """接力单上一单乘客操作修改目的地、收到该回调建议查询订单详情，更新上一单目的地经纬度"""
    RESERVATION_ORDER_MODIFY_PASSENGER_INFO = 47
    """曹操客服按照用户要求修改预约单用车时间或乘客号码，修改后司机虚拟号将发生变更（当前仅 API 接入有此事件回调）"""
    RELAY_ORDER_PREVIOUS_SERVICE_COMPLETE = 48
    """接力单上一单司机服务完成，此时司机开始服务当前订单"""

    @property
    def _STATUS_UPDATED_EVENT(self) -> List[int]:
        """
        发生了状态变化的事件
        """
        return (
            self.DRIVER_ACCEPT_ORDER,
            self.DRIVER_START_SERVICE,
            self.DRIVER_ARRIVED,
            self.DRIVER_START_BILLING,
            self.DRIVER_END_BILLING,
            self.DRIVER_INPUT_EXTRA_FEE,
            self.USER_PAYMENT,
            self.USER_REVIEW,
            self.CASH_PAYMENT,
            self.CUSTOMER_SERVICE_CANCEL,
            self.USER_CANCEL,
            self.SYSTEM_CANCEL,
            self.DRIVER_CANCEL,
            self.THIRD_PARTY_CANCEL,
            self.DRIVER_INITIATE_REASSIGN,
            self.DRIVER_REASSIGN_FAILED,
            self.DRIVER_REASSIGN_SUCCESS,
            self.USER_PAY_CANCEL_FEE,
            self.CUSTOMER_SERVICE_EXEMPTION,
            self.RELAY_ORDER_PREVIOUS_SERVICE_COMPLETE
        )

    def to_caocao_order_status(self) -> CaocaoOrderStatus:

        """
        转换为曹操出行订单状态（前提是引起了状态转换）
        """
        if self not in self._STATUS_UPDATED_EVENT:
            return None

        if self == self.DRIVER_ACCEPT_ORDER:
            return CaocaoOrderStatus.ASSIGNED
        elif self == self.DRIVER_START_SERVICE:
            return CaocaoOrderStatus.SERVICE_STARTED
        elif self == self.DRIVER_ARRIVED:
            return CaocaoOrderStatus.DRIVER_ARRIVED
        elif self == self.DRIVER_START_BILLING:
            return CaocaoOrderStatus.PASSENGER_ONBOARD
        elif self == self.DRIVER_END_BILLING:
            return CaocaoOrderStatus.TRIP_ENDED
        elif self == self.DRIVER_INPUT_EXTRA_FEE:
            return CaocaoOrderStatus.TRIP_ENDED
        elif self == self.USER_PAYMENT:
            return CaocaoOrderStatus.PENDING_REVIEW
        elif self == self.USER_REVIEW:
            return CaocaoOrderStatus.REVIEWED
        elif self == self.CASH_PAYMENT:
            return CaocaoOrderStatus.PENDING_REVIEW
        elif self == self.CUSTOMER_SERVICE_CANCEL:
            return CaocaoOrderStatus.CUSTOMER_SERVICE_CANCELLED
        elif self == self.SYSTEM_CANCEL:
            return CaocaoOrderStatus.SYSTEM_CANCELLED
        elif self == self.USER_CANCEL:
            return CaocaoOrderStatus.USER_CANCELLED
        elif self == self.DRIVER_CANCEL:
            return CaocaoOrderStatus.DRIVER_CANCELLED
        elif self == self.THIRD_PARTY_CANCEL:
            return CaocaoOrderStatus.THIRD_PARTY_CANCELLED
        elif self == self.DRIVER_INITIATE_REASSIGN:
            return CaocaoOrderStatus.REASSIGNING
        elif self == self.DRIVER_REASSIGN_FAILED:
            return CaocaoOrderStatus.DRIVER_CANCELLED
        elif self == self.DRIVER_REASSIGN_SUCCESS:
            return CaocaoOrderStatus.ASSIGNED
        elif self == self.USER_PAY_CANCEL_FEE:
            return CaocaoOrderStatus.CANCELLED_PAID
        elif self == self.CUSTOMER_SERVICE_EXEMPTION:
            return CaocaoOrderStatus.CANCELLED_NO_FEE
        elif self == self.RELAY_ORDER_PREVIOUS_SERVICE_COMPLETE:
            return CaocaoOrderStatus.SERVICE_STARTED
    
    @property
    def is_status_updated(self) -> bool:

        """
        该事件是否表明订单状态发生变化
        """
        return self in self._STATUS_UPDATED_EVENT



class CaocaoCallback(BaseModel):

    """
    曹操出行回调通知
    """
    timestamp: int
    """毫秒时间戳"""
    sign: str
    """签名"""
    order_id: str
    """订单ID"""
    ext_order_id: str
    """外部订单ID"""
    event: CaocaoCallbackEvent
