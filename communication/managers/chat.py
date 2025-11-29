"""聊天管理器

Business logic for chat operations using SQLModel and FastAPI patterns.
"""

__all__ = ["ChatManager"]

import json
import typing
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from ..schemas.chat import Chat, ChatRef, ChatType, ChatStatus
from ..schemas.message import Message

if typing.TYPE_CHECKING:
    from main.schemas.partner_request import PartnerRequest
    from main.schemas.partner_request.application import PartnerApplication


class ChatManager:
    """Chat business logic manager.

    Provides methods for chat operations without BlueFirmament dependencies.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, chat_id: ChatRef) -> Opt[Chat]:
        """Get a chat by ID."""
        with SessionLocal() as db:
            return db.get(Chat, chat_id)

    @classmethod
    def get_members(cls, chat_id: ChatRef) -> set[AccountRef]:
        """获取聊天成员列表

        :param chat_id: 聊天 ID
        :return: 成员 ID 集合
        """
        with SessionLocal() as db:
            chat = db.get(Chat, chat_id)
            if not chat:
                return set()
            if chat.members is None:
                return set()
            members_list = json.loads(chat.members)
            return set(members_list)

    @classmethod
    def is_member(cls, chat_id: ChatRef, account_id: AccountRef) -> bool:
        """检查用户是否为聊天成员

        :param chat_id: 聊天 ID
        :param account_id: 账号 ID
        :return: 是否为成员
        """
        members = cls.get_members(chat_id)
        return account_id in members

    @classmethod
    def get_chat_messages(
        cls,
        chat_id: ChatRef,
        start: int = 0,
        offset: int = 6,
        desc: bool = True,
    ) -> list[Message]:
        """获取聊天历史消息

        :param chat_id: 聊天 ID
        :param start: 起始位置
        :param offset: 获取数量
        :param desc: 是否降序排列
        :return: 消息列表
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Message).where(Message.chat == chat_id)
            if desc:
                statement = statement.order_by(Message.id.desc())
            else:
                statement = statement.order_by(Message.id)
            statement = statement.offset(start).limit(offset)
            messages = db.exec(statement).all()
            return list(messages)

    @classmethod
    def get_user_chats(
        cls,
        user_id: AccountRef,
        chat_type: Opt[ChatType] = None,
    ) -> list[ChatRef]:
        """获取用户的聊天列表

        :param user_id: 用户 ID
        :param chat_type: 聊天类型过滤
        :return: 聊天 ID 列表
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Chat.id).where(Chat.created_by == user_id)
            if chat_type:
                statement = statement.where(Chat.type == chat_type.value)
            results = db.exec(statement).all()
            return list(results)

    @classmethod
    def create_dm_chat(
        cls,
        from_id: AccountRef,
        to_id: AccountRef,
    ) -> tuple[Chat, bool]:
        """创建私信聊天

        如果两者已经存在私信聊天，则返回已存在的聊天

        :param from_id: 发起者 ID
        :param to_id: 目标用户 ID
        :return: (聊天对象, 是否新创建)
        :raises ValueError: 如果试图与自己创建私信
        """
        if from_id == to_id:
            raise ValueError("cannot create a direct message chat with yourself")

        with SessionLocal() as db:
            # 尝试查找已存在的私信聊天
            statement = sqlmodel.select(Chat).where(
                Chat.type == ChatType.DIRECT_MESSAGE.value
            )
            chats = db.exec(statement).all()

            for chat in chats:
                if chat.members:
                    members = set(json.loads(chat.members))
                    if {from_id, to_id} == members:
                        return chat, False

            # 创建新的私信聊天
            members_json = json.dumps([from_id, to_id])
            chat = Chat(
                type=ChatType.DIRECT_MESSAGE.value,
                created_by=from_id,
                members=members_json,
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return chat, True

    @classmethod
    def create_pr_chat(cls, partner_request: "PartnerRequest") -> Chat:
        """创建搭子请求群聊

        :param partner_request: 搭子请求
        :return: 创建的聊天
        """
        with SessionLocal() as db:
            chat = Chat(
                type=ChatType.PARTNER_REQUEST.value,
                created_by=partner_request.created_by,
                members=None,
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return chat

    @classmethod
    def create_partner_application_chat(
        cls,
        application: "PartnerApplication",
        pr_chat_id: ChatRef,
    ) -> Chat:
        """创建搭子申请群聊

        :param application: 搭子申请
        :param pr_chat_id: 搭子请求群聊 ID
        :return: 创建的聊天
        """
        with SessionLocal() as db:
            chat = Chat(
                type=ChatType.PARTNER_APPLICATION.value,
                created_by=application.applicant,
                parent=pr_chat_id,
                members=None,
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return chat

    @classmethod
    def close_chat(cls, chat_id: ChatRef) -> Opt[Chat]:
        """关闭群聊

        :param chat_id: 聊天 ID
        :return: 更新后的聊天对象，如果不存在则返回 None
        """
        with SessionLocal() as db:
            chat = db.get(Chat, chat_id)
            if not chat:
                return None
            chat.status = ChatStatus.CLOSED.value
            db.add(chat)
            db.commit()
            db.refresh(chat)
            return chat

