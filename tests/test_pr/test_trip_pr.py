from calendar import c
import datetime
import uuid
import jwt
import pytest

import data.settings.auth
from blue_firmament.task.main import Task, TaskID, TaskMetadata, TaskParameters
from blue_firmament.task.result import TaskResult
from blue_firmament.task.context.common import CommonTaskContext
from blue_firmament.task.context import BaseTaskContext
from blue_firmament.log import get_logger
from blue_firmament.utils.datetime_ import get_datetimez
from blue_firmament.data.settings.auth import get_setting as get_auth_setting
from interface_main.schemas.partner_request import (
    PartnerRequestRef, PartnerRequest, PartnerRequestL2Type,
    PartnerRequestStatus
)
from interface_main.schemas.chat import Chat, ChatType
from interface_main.schemas.partner_request.trip.ride_hailing import RideHailingPRContent
from interface_main.schemas.base.route import RouteItem, RouteItemDatetime
from interface_main.dal import SupabaseServPostgrest
from app.managers.partner_request.trip.ride_hailing import RideHailingPRManager
LOGGER = get_logger(__name__)



@pytest.fixture
def user_id() -> str:
    return "d823f092-5400-4b96-a1ac-4ad52d2b8162"

@pytest.fixture
def user_jwt(user_id) -> str:
    return  jwt.PyJWT().encode(
        {
            "role": "authenticated",
            "aud": "authenticated",
            "exp": get_datetimez().timestamp() + 1000,
            "iat": get_datetimez().timestamp(),
            "session_id": uuid.uuid4().hex,
            "sub": user_id
        },
        key=get_auth_setting().jwt_secret_key,
        algorithm=get_auth_setting().jwt_algorithms[0],
    )

@pytest.fixture
def serv_jwt(user_id) -> str:
    return  jwt.PyJWT().encode(
        {
            "role": "service_role",
            "aud": "authenticated",
            "exp": get_datetimez().timestamp() + 1000,
            "iat": get_datetimez().timestamp(),
            "session_id": uuid.uuid4().hex,
            "sub": user_id
        },
        key=get_auth_setting().jwt_secret_key,
        algorithm=get_auth_setting().jwt_algorithms[0],
    )

@pytest.fixture
def task_context(user_jwt) -> CommonTaskContext:
    return CommonTaskContext(
        tc=BaseTaskContext(
            task_result=TaskResult(),
            task=Task(
                task_id=TaskID(None, ""),
                metadata=TaskMetadata(
                    authorization=("Bearer", user_jwt)
                )
            ),
            base_logger=LOGGER
        )
    )

@pytest.fixture
async def pr_id(user_id, task_context, serv_jwt):
    class A:
        access_token = serv_jwt
    dal = SupabaseServPostgrest(auth_session=A())

    chat = await dal.insert(
        Chat(
            _task_context=task_context,
            _id=0,
            type=ChatType.PARTNER_REQUEST,
            created_by=user_id,
            members=None
        )
    )

    to_match_pr = await dal.insert(
        PartnerRequest(
            _task_context=task_context,
            _id=PartnerRequestRef(0),
            type=PartnerRequestL2Type.RIDE_HAILING,
            status=PartnerRequestStatus.JOINABLE,
            chat=chat._id,
            created_by=user_id,
        )
    )

    await dal.insert(
        RideHailingPRContent(
            _task_context=task_context,
            _id=to_match_pr._id,
            route=[
                RouteItem(
                    datetime=RouteItemDatetime(
                        datetime=get_datetimez() + datetime.timedelta(hours=1),
                        time=None,
                        bring_ahead=0,
                        put_off=5
                    ),
                    location="3859b2550b129f143efb4920e4addb73"
                ),
                RouteItem(
                    datetime=RouteItemDatetime(),
                    location="b05a1836f08d48dc1c9be2f94c37a714"
                )
            ]
        )
    )

    matchable_pr = await dal.insert(
        PartnerRequest(
            _task_context=task_context,
            _id=PartnerRequestRef(0),
            type=PartnerRequestL2Type.RIDE_HAILING,
            status=PartnerRequestStatus.JOINABLE,
            created_by="71482aef-69a5-41cd-b408-66b6da812ec9",  # Different user to ensure no conflict
            chat=chat._id,
        )
    )

    await dal.insert(
        RideHailingPRContent(
            _task_context=task_context,
            _id=matchable_pr._id,
            route=[
                RouteItem(
                    datetime=RouteItemDatetime(
                        datetime=get_datetimez() + datetime.timedelta(hours=1),
                        time=None,
                        bring_ahead=20,
                        put_off=0
                    ),
                    location="68f9ed41ef5e2f17f7f2195b384bc3b4"
                ),
                RouteItem(
                    datetime=RouteItemDatetime(),
                    location="b05a1836f08d48dc1c9be2f94c37a714"
                )
            ]
        )
    )

    yield PartnerRequestRef(to_match_pr._id), PartnerRequestRef(matchable_pr._id)

    await dal.delete(to_match_pr)
    await dal.delete(matchable_pr)
    await dal.delete(chat)


async def test_get_matched_prs(
    pr_id,
    task_context: CommonTaskContext
):
    """测试出行搭子请求的内发现

    Cases:
    - 路线一致，在时间窗口内 -> 匹配
    - 路线可合并，在时间窗口内 -> 匹配
    - 近距离点合并
    - 不在时间窗口内 -> 不匹配
    """
    # manager instance
    pr_manager = RideHailingPRManager(task_context)

    # call
    res = await pr_manager.get_MR_content(pr_id[0])

    # assert
    assert type(res) is tuple
    assert len(res) == 1  # FIXME more than one
    assert res[0][1] == pr_id[1]
