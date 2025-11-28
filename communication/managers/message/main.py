"""消息管理器

Business logic for message operations using SQLModel and FastAPI patterns.
"""

__all__ = [
    "MessageManager",
]

import json
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from ...schemas.chat import ChatRef
from ...schemas.message import Message, MessageRef, MessageType


class MessageManager:
    """Message business logic manager.

    Provides methods for message operations without BlueFirmament dependencies.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, message_id: MessageRef) -> Opt[Message]:
        """Get a message by ID."""
        with SessionLocal() as db:
            return db.get(Message, message_id)

    @classmethod
    def get_chat_messages(
        cls,
        chat_id: ChatRef,
        start: int = 0,
        offset: int = 6,
        desc: bool = True,
    ) -> list[Message]:
        """获取聊天的消息

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
    def send_plain_message(
        cls,
        chat_id: ChatRef,
        created_by: AccountRef,
        content: str,
    ) -> Message:
        """发送纯文本消息

        :param chat_id: 聊天 ID
        :param created_by: 发送者 ID
        :param content: 消息内容
        :return: 创建的消息
        """
        with SessionLocal() as db:
            message = Message(
                chat=chat_id,
                created_by=created_by,
                type=MessageType.PLAIN.value,
                content=content,
            )
            db.add(message)
            db.commit()
            db.refresh(message)
            return message

    @classmethod
    def mark_as_viewed(
        cls,
        message_id: MessageRef,
        user_id: AccountRef,
    ) -> Opt[Message]:
        """标记消息已读

        :param message_id: 消息 ID
        :param user_id: 用户 ID
        :return: 更新后的消息，如果不存在则返回 None
        """
        with SessionLocal() as db:
            message = db.get(Message, message_id)
            if not message:
                return None

            viewed = json.loads(message.viewed) if message.viewed else []
            if user_id not in viewed:
                viewed.append(user_id)
                message.viewed = json.dumps(viewed)
                db.add(message)
                db.commit()
                db.refresh(message)
            return message
