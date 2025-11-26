"""通勤搭子请求管理器"""

__module_name__ = "CommutePartnerRequestManager"

# typing
from ..base import TypedPRManager, BasePRManager
from blue_firmament.scheme import merge_scheme
from communication.managers.message.main import BaseMessageManager
from .base import TripPRManager

# from interface_ride_hailing.schemas.order import RideHailingOrderStatus
from ....schemas.partner_request import PartnerRequestStatus, PartnerRequestRef
from ....schemas.partner_request.trip.commute import (
    CommutePartnerRequest,
    CommutePRContent,
    CommutePREditable,
)
from blue_firmament import listen_to, Method
from blue_firmament.log import get_logger

logger = get_logger(__module_name__)


class CommutePRManager(
    TripPRManager,
    TypedPRManager[CommutePRContent, CommutePartnerRequest],
    path_prefix=BasePRManager.__path_prefix__ + "/commute",
    scheme_cls=CommutePRContent,
    typed_cls=CommutePartnerRequest,
):
    """通勤搭子请求管理器"""

    @listen_to(Method.POST, "")
    async def create(self, body: CommutePREditable) -> CommutePartnerRequest:
        return await TypedPRManager._create(
            self,
            base_editable=body,
            content=CommutePRContent(
                _id=PartnerRequestRef(0),
                route=body.route,
                trip_preference=body.trip_preference,
                on_at=body.on_at,
                off_at=body.off_at,
                workdays=body.workdays,
            ),
        )

    @listen_to(Method.PUT, "/{partner_request_id}")
    async def update(
        self, body: CommutePREditable, partner_request_id: PartnerRequestRef
    ) -> CommutePartnerRequest:
        content = await self._get_scheme(_id=partner_request_id)
        merge_scheme(content, body)

        return await super()._update(
            pr_id=partner_request_id, base_editable=body, content=content
        )

    def handle_ride_hailing_order_callback(self, ride_hailing_order_id: int, status):
        """
        处理网约车订单状态回调

        TODO
        """
        logger.info("Handle ride hailed")

        if ride_hailing_order_id not in self.schema.ride_hailing_orders:
            # 绑定未绑定的
            self.schema.ride_hailing_orders.append(ride_hailing_order_id)

        # 按照新的网约车订单状态更新搭子请求相关数据
        if status in (RideHailingOrderStatus.CANCELLED, RideHailingOrderStatus.ERROR):
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
            # 下一个循环；如果要关闭该搭子请求，则另外调用关闭方法
            self.schema.status = PartnerRequestStatus.WAITING_FOR_EXECUTION

        supabase_serv_db.update(
            table_name=self._table,
            schema=self._db_schema,
            to_update={"status": self.schema.status.value},
            filters=(("eq", ("_id", self.id)),),
            logger=logger,
        )
        supabase_serv_db.update(
            table_name=self._sub_table,
            schema=self._db_schema,
            to_update={"ride_hailing_orders": self.schema.ride_hailing_orders},
            filters=(("eq", ("_id", self.id)),),
            logger=logger,
        )

        # 发送网约车订单状态更新消息
        BaseMessageManager.send_ride_hailing_order_status_update_message(
            chat_id=self.schema.chat, new_status=status
        )
