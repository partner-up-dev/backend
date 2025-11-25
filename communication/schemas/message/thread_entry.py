from ..chat import ChatRef
from blue_firmament.scheme import BaseScheme


class ThreadEntry(BaseScheme, proxy=False):
    """聊天邀请

    存储于 message.content 中
    """

    chat: ChatRef
    description: str
