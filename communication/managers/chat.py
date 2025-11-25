"""聊天管理器"""

import typing
from typing import Annotated as Anno, Literal as Lit, Optional as Opt

from dal import DefaultRedis
from blue_firmament import Method, listen_to
from blue_firmament.exceptions import Forbidden, NotFound, ParamsInvalid, Conflict
from blue_firmament.log import get_logger
from blue_firmament.manager import CommonManager, PresetHandlerConfig
from blue_firmament.scheme.converter import IntConverter
from blue_firmament.task import TaskStatus
from blue_firmament.task.result import StreamingBody, PlainTextBody
from account.schemas import AccountRef
from ..schemas.chat import Chat, ChatRef, ChatType
from ..schemas.message import Message
from main.schemas.partner_request import PartnerRequest

if typing.TYPE_CHECKING:
    from main.schemas.partner_request.application import PartnerApplication

LOGGER = get_logger(__name__)


class ChatManager(
    CommonManager[Chat, ChatRef],
    scheme_cls=Chat,
    manager_name="chat",
    path_prefix="chat",
    preset_handler_config=PresetHandlerConfig(get=True),
):
    async def _must_be_member(
        self, chat_id: Opt[ChatRef] = None, account_id: Opt[AccountRef] = None
    ) -> None:
        """必须为聊天成员

        :param chat_id: 聊天 ID
        :raise Forbidden: 如果不是成员
        """
        account_id = account_id or AccountRef(self._operator.id)
        chat = await self._get_scheme(_id=chat_id)
        if account_id not in (await chat.get_members()):
            raise Forbidden("must be a member of the chat")

    @listen_to(Method.GET, "/{chat_id}/messages")
    async def get_history(
        self,
        chat_id: ChatRef,
        start: Anno[int, IntConverter(ge=0)] = 0,
        offset: Anno[int, IntConverter(ge=1, le=12)] = 6,
        desc: bool = True,
    ) -> typing.Tuple[Message, ...]:
        """获取聊天历史消息

        :param desc: 是否降序排列

        条件：
        - 必须是聊天的成员
        """
        await self._must_be_member(chat_id=chat_id)
        from .message import BaseMessageManager

        return await BaseMessageManager(self).get_chat_messages(
            chat_id=chat_id, start=start, offset=offset, desc=desc
        )

    async def get_members(self, chat_id: Opt[ChatRef] = None) -> set[AccountRef]:
        """获取聊天成员列表"""
        self._scheme = await self._get_scheme(chat_id)
        return await self._scheme.get_members()

    @listen_to(Method.GET, "/mine")
    async def get_mine(
        self, chat_type: Opt[ChatType] = None, return_in: Lit["id", "full"] = "id"
    ) -> tuple[ChatRef | Chat, ...]:
        """获取我的聊天

        :param chat_type: 聊天类型
        :param return_in: 返回类型，默认为 ID 列表
            - "id": 仅返回聊天 ID 列表
            - "full": 返回完整的聊天对象列表
        :return: 聊天列表

        Docs
        ----
        - `APIFOX <https://app.apifox.com/link/project/4406548/apis/api-275041592>`_
        """
        query_coms = (Chat.type.equals(chat_type),) if chat_type else ()
        if return_in == "full":
            return await self._dao.select(*query_coms)
        elif return_in == "id":
            return await self._dao.select_field(Chat._id, *query_coms)
        raise ParamsInvalid("unsupported", return_in=return_in)

    @listen_to(Method.PUT, "/direct_message/{to_id}")
    async def create_dm_chat(
        self,
        to_id: AccountRef,
        from_id: Opt[AccountRef] = None,
    ) -> Chat:
        """创建私信聊天

        如果两者已经存在私信聊天，则返回已存在的聊天

        :param to_id: 私聊对象
        :param from_id: 私聊发起者
        """
        from_id = from_id or AccountRef(self._operator.id)  # TODO use param getter (resolver)

        if from_id == to_id:
            raise Conflict("cannot create a direct message chat with yourself")

        try:
            self._scheme = await self._dao.select_one(
                Chat.type.equals(ChatType.DIRECT_MESSAGE),
                Chat.members.contains(to_id, from_id),
            )
        except NotFound:
            # 创建私信聊天
            self._scheme = await self.insert(
                Chat(
                    _task_context=self,
                    _id=ChatRef(0),
                    type=ChatType.DIRECT_MESSAGE,
                    created_by=from_id,
                    members={to_id, from_id},
                )
            )
            self._task_result.status = TaskStatus.CREATED

        return self._scheme

    async def create_pr_chat(self, partner_request: PartnerRequest) -> Chat:
        """创建搭子请求群聊

        - 创建者是搭子请求的创建者
        - 成员列表为 None
        """
        return await self.insert(
            Chat(
                _id=ChatRef(0),
                type=ChatType.PARTNER_REQUEST,
                created_by=partner_request.created_by,
                members=None,
            )
        )

    async def create_partner_application_chat(
        self,
        application: "PartnerApplication",
        pr_chat_id: ChatRef,
    ) -> Chat:
        """创建搭子申请群聊

        1. 创建搭子申请群聊
        3. 链接搭子申请群聊到搭子请求群聊的子群聊中

        :param application: 搭子申请
        :param pr_chat_id: 搭子请求群聊 ID
        """
        # 1. create chat
        chat = await self.insert(
            Chat(
                _id=ChatRef(0),
                type=ChatType.PARTNER_APPLICATION,
                created_by=application.applicant,
                parent=pr_chat_id,  # 链接到搭子请求群聊
                members=None,
            )
        )

        return chat

    @listen_to(Method.GET, "/unread")
    async def get_my_unread(
        self,
    ) -> StreamingBody:
        """持续获取未读消息"""
        redis = DefaultRedis()
        listen_to_queue = f"unread_messages:{self._operator.id}"

        # await redis.subscribe(*listen_to_channels)

        stop = False

        async def _get_my_unread() -> StreamingBody.GeneratorType:
            while not stop:
                # message = await redis.get_message()
                message_id = await redis.pop(listen_to_queue)
                yield PlainTextBody(message_id.decode("utf-8"))
            self._logger.info("Stop listening for unread messages")

        async def _cleanup() -> None:
            nonlocal stop
            stop = True
            await redis.close()

        return StreamingBody(
            generator=_get_my_unread(),
            cleanup=_cleanup,
        )

    async def close(self, chat_id: Opt[ChatRef] = None) -> Chat:
        """关闭群聊"""
        self._scheme = await self._get_scheme(_id=chat_id)
        self._scheme.status = self._scheme.status.to_closed()
        return await self._update_scheme()
