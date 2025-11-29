"""聊天邀请数据模型"""

from pydantic import BaseModel

from ..chat import ChatRef


class ThreadEntry(BaseModel):
    """聊天邀请

    存储于 message.content 中（JSON序列化）
    """

    chat: ChatRef
    description: str
