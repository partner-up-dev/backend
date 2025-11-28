"""网约车搭子请求管理器"""

__module_name__ = "RideHailingPartnerRequestManager"

from ..base import BasePRManager, TypedPRManager
from blue_firmament.scheme import merge_scheme
from blue_firmament.exceptions import DuplicateOrConflict
from communication.managers.message.main import BaseMessageManager
from .base import TripPRManager

# from interface_ride_hailing.schemas.order import RideHailingOrderStatus
from ....schemas.partner_request import PartnerRequestStatus, PartnerRequestRef
from ....schemas.partner_request.trip.ride_hailing import (
    RideHailingPartnerRequest,
    RideHailingPREditable,
    RideHailingPRContent,
)
from blue_firmament import listen_to, Method
from blue_firmament.log import get_logger

LOGGER = get_logger(__module_name__)


class RideHailingPRManager(
    TripPRManager,
    TypedPRManager[RideHailingPRContent, RideHailingPartnerRequest],
    path_prefix=BasePRManager.__path_prefix__ + "/ride_hailing",
    scheme_cls=RideHailingPRContent,
    typed_cls=RideHailingPartnerRequest,
):
    """网约车搭子请求管理器"""

    @listen_to(Method.POST, "")
    async def create(self, body: RideHailingPREditable) -> RideHailingPartnerRequest:
        return await TypedPRManager._create(
            self,
            base_editable=body,
            content=RideHailingPRContent(_id=PartnerRequestRef(0), **body.dump_to_dict()),
        )

    @listen_to(Method.PUT, "/{partner_request_id}")
    async def update(
        self, body: RideHailingPREditable, partner_request_id: PartnerRequestRef
    ) -> RideHailingPartnerRequest:
        content = await self._get_scheme(_id=partner_request_id)
        merge_scheme(content, body)

        return await TypedPRManager._update(
            self, pr_id=partner_request_id, base_editable=body, content=content
        )

    async def get_MR_content(self, pr_id):
        res = await TripPRManager.get_MR_content(self, pr_id)

        # TODO ride_hailing preferences match

        return res

    def handle_ride_hailing_order_callback(self, ride_hailing_order_id: int, status):
        """
        处理网约车订单状态回调

        1. 相应地更新状态以及对应数据
        2. 发送通知（作为函数返回，调用者加入到任务队列中）
        """
        LOGGER.info("Handle ride hailed")

        # 防止重复绑定；防止处理不是绑定的订单的状态回调
        if self.schema.ride_hailing_order is not None:
            if (order_id := self.schema.ride_hailing_order) and order_id != ride_hailing_order_id:
                raise DuplicateOrConflict("The partner request already has a ride hailing order")
        else:
            # 绑定
            self.schema.ride_hailing_order = ride_hailing_order_id

        # 按照新的网约车订单状态更新搭子请求相关数据
        if status in (RideHailingOrderStatus.CANCELLED, RideHailingOrderStatus.ERROR):
            self.schema.ride_hailing_order = None  # 解绑
            self.schema.status = PartnerRequestStatus.WAITING_FOR_EXECUTION  # 状态回退
        elif status in (
            RideHailingOrderStatus.PENDING,
            RideHailingOrderStatus.DISPATCHING,
            RideHailingOrderStatus.COMPETING,
            RideHailingOrderStatus.ACCEPTED,
            RideHailingOrderStatus.PICKING_UP,
            RideHailingOrderStatus.PICKED,
            RideHailingOrderStatus.ARRIVED,
            RideHailingOrderStatus.IN_PROGRESS,
            RideHailingOrderStatus.DROPPED,
        ):
            self.schema.status = PartnerRequestStatus.EXECUTING
        elif status in (RideHailingOrderStatus.UNPAID,):
            self.schema.status = PartnerRequestStatus.CLOSING
        elif status in (RideHailingOrderStatus.CLOSED, RideHailingOrderStatus.REVIEW_OPENING):
            self.schema.status = PartnerRequestStatus.CLOSED

        supabase_serv_db.update(
            table_name=self._table,
            schema=self._db_schema,
            to_update={"status": self.schema.status.value},
            filters=(("eq", ("_id", self.id)),),
            logger=LOGGER,
        )
        supabase_serv_db.update(
            table_name=self._sub_table,
            schema=self._db_schema,
            to_update={"ride_hailing_order": self.schema.ride_hailing_order},
            filters=(("eq", ("_id", self.id)),),
            logger=LOGGER,
        )

        # 发送网约车订单状态更新消息
        BaseMessageManager.send_ride_hailing_order_status_update_message(
            chat_id=self.schema.chat, new_status=status
        )
