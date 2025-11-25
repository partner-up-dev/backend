"""Tests of Chat/Notification Module
"""

from app.managers.chat.notification import NotificationManager
from interface_main.schemas.partner_request.application import PartnerApplication, PartnerApplicationRef
from blue_firmament.task.context import CommonTaskContext, BaseTaskContext
from blue_firmament.task import Task, TaskID, TaskResult
from blue_firmament.log import get_logger

TEST_LOGGER = get_logger(__name__)

def test_send():
    NotificationManager(CommonTaskContext(
        BaseTaskContext(
            task=Task(
                task_id=TaskID(None, "")
            ),
            task_result=TaskResult(),
            base_logger=TEST_LOGGER,
        )
    )).send(
        PartnerApplication(
            _id=PartnerApplicationRef(0),
            
        )
    )

