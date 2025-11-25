"""通知模块测试
"""
from blue_firmament.task import Task, TaskID, TaskResult
from blue_firmament.task.context import BaseTaskContext
from blue_firmament.log import get_logger

from app.managers.notification.main import NotificationManager
from managers.notification.channel.weixin import PartnerUpMPWXSubMessage, WXMPSubMessageContent
from managers.notification.channel import weixin
from managers.notification.main import NotificationContent, NotificationTask


async def test_send():

    class MockAccountManager:
        TABLE = {
            "25ba3ed1-9f9a-4254-81a9-44363b66d20a": "oK1ud60ucpOmISARoW0qnqJnYoAw",
            "5abf7121-c9aa-4368-b94c-dcf1bb5fe46f": "oK1ud60EjOXZQ6iH72NjwWC01ors",
            "f2db3156-b3df-4bc7-a48e-22fd77a6616c": "oK1ud62mEB8g96ov_PYz_Ye2YRws"
        }

        def __init__(self, btc):
            pass

        async def get_wxmp_openid(self, user_id: str) -> str:
            return self.TABLE[user_id]

    weixin.AccountManager = MockAccountManager

    class NewPartnerApplication(NotificationContent):

        def to_wxmp_submessage(self):
            return WXMPSubMessageContent(
                # to_user need to subscribe the template
                template_id="f8ObZSVYpzUsZ9RU3zgwHYkJj674vDttSJtT19v7leA",
                data={
                    "name1": {
                        "value": "袁翊闳"
                    },
                    "name2": {
                        "value": "广外南去广州南站"
                    },
                    "thing5": {
                        "value": "请尽快前往审批"
                    }
                }
            )

        def to_wxsa_submessage(self):
            raise NotImplementedError

    await NotificationManager(BaseTaskContext(
        task=Task(
            task_id=TaskID("POST", "/test/notification/send"),
        ),
        task_result=TaskResult(),
        base_logger=get_logger("test.notification.main")
    )).send(NotificationTask(
        to=("f2db3156-b3df-4bc7-a48e-22fd77a6616c",),
        channel=PartnerUpMPWXSubMessage,
        content=NewPartnerApplication()
    ))

    # TODO test WXSASubMessage Channel
