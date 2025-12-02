"""沟通模块的数据模型"""

__all__ = [
    # chat
    "Chat",
    "ChatRef",
    "ChatStatus",
    "ChatType",
    # message
    "Message",
    "MessageRef",
    "MessageEditable",
    "MessageType",
    # message sub-schemas
    "ThreadEntry",
    "Approval",
    "ApprovalType",
    "ApprovalStatus",
    "VotesT",
    # notifications
    "NotificationContent",
    "NotificationTask",
    "WXMPSubMessageContent",
    "WXSASubMessageContent",
]

from .chat import Chat, ChatRef, ChatStatus, ChatType
from .message import Message, MessageRef, MessageEditable, MessageType
from .message.thread_entry import ThreadEntry
from .message.approval import Approval, ApprovalType, ApprovalStatus, VotesT
from .notification import (
    NotificationContent,
    NotificationTask,
    WXMPSubMessageContent,
    WXSASubMessageContent,
)
