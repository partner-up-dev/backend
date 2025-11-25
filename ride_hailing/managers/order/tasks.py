from celery_app import celery_app
from backend_common.libs.database import supabase_serv_db
from backend_common.libs.logs import top_logger as logging
from interface_main.apis.partner_request import v1_pr_ride_hailing_order_status_callback
from interface_main.apis.split_the_bill import v1_split_bill_cancel, SplitBillCancelReason
from backend_common.utils.auth import get_assistant_identity_provider
from app.schemas.order import RideHailingOrderStatus, PlatformCancelReason
from backend_common.libs.exceptions import NotFound
import datetime
from data.settings.models.order import get_setting as get_order_setting
from backend_common.utils.datetime import get_datetimez

logger = logging.getChild("OrderTasks")

@celery_app.task(bind=True, max_retries=5, default_retry_delay=10)
def send_status_callback_to_pr(self, order_id: int):

    """
    发送网约车订单状态回调到搭子请求
    """
    from app.managers.order import OrderManager

    try:
        fetch_result = supabase_serv_db.fetch(
            schema=OrderManager._DB_SCHEMA,
            table_name=OrderManager._TABLE,
            columns=['partner_request', 'status'],
            filters=(("eq", ("_id", order_id)),),
            logger=logger
        )

        partner_request_id = fetch_result[0]["partner_request"]
        if not partner_request_id:
            logger.warning(f"Order {order_id} has no partner request")
            return
        
        logger.info(f"Send ride hailing order status callback of order{order_id} in status {fetch_result[0]['status']}")

        v1_pr_ride_hailing_order_status_callback( 
            partner_request_id=partner_request_id,
            ride_hailing_order_id=order_id,
            status=fetch_result[0]["status"],
            identity_provider=get_assistant_identity_provider()
        )
    except Exception as e:
        countdown = 5 ** self.request.retries  # exponential backoff
        raise self.retry(exc=e, countdown=countdown)
    
@celery_app.task(bind=True, max_retries=5, default_retry_delay=10)
def cancel_split_bill(self, order_id: int):

    """
    取消对应的平账账单（以payer_disabled为由）
    """
    from app.managers.order import OrderManager

    try:
        fetch_result = supabase_serv_db.fetch(
            schema=OrderManager._DB_SCHEMA,
            table_name=OrderManager._TABLE,
            columns=['split_bill'],
            filters=(("eq", ("_id", order_id)),),
            logger=logger
        )

        if fetch_result[0]["split_bill"]:
            v1_split_bill_cancel(
                split_bill_id=fetch_result[0]["split_bill"],
                reason=SplitBillCancelReason.PAYER_DISABLED,
                identity_provider=get_assistant_identity_provider()
            )
        else:
            logger.warning(f"Order {order_id} has no split bill")
    except Exception as e:
        countdown = 5 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown)
    
@celery_app.task
def check_timeout_dispatching_order():
    logger.info("Checking for timeout dispatching orders and cancel them")

    # Fetch all expirable SplitBills
    try:
        from app.managers.order import OrderManager
        disptaching_orders = supabase_serv_db.fetch(
            schema=OrderManager._DB_SCHEMA,
            table_name=OrderManager._TABLE,
            columns=['_id', 'timeline'],
            filters=(
                ("in_", ("status", (RideHailingOrderStatus.DISPATCHING.value,))),
            ),
            logger=logger
        )
    except NotFound:
        return
    else:
        for data in disptaching_orders:
            try:
                try:
                    dispatch_time_str: str = data["timeline"]["dispatch"]
                except KeyError:
                    logger.warning(f"Order {data['_id']} has no dispatch time, skip it")
                else:
                    if ((
                        get_datetimez(iso8601=dispatch_time_str) - get_datetimez()
                    ).total_seconds() / 60) >= get_order_setting().disptach_timeout:
                        logger.info(f"Order {data['_id']} is timeout in dispatching, cancel it")
                        order_manager = OrderManager(data["_id"])
                        order_manager.cancel(reason=PlatformCancelReason.COMPETITORS_UNRESPONSIVE)
            except Exception as e:
                logger.error(f"Failed to handle timeout dispatching order {data['_id']}: {e}, skip first")
                continue