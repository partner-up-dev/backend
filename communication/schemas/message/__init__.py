"""消息模块的数据模型
"""

__all__ = [
    "Message", 
    "MessageRef", 
    "MessageEditable",
    "MessageTV",
    "MessageType",
    "PlainMessage", 
    "PartnerApplicationMessage",
    "SplitBillMessage",
    "ThreadEntryMessage", 
    "ApprovalMessage",
]

from .main import (
    MessageType, 
    MessageRef,
    Message, 
    MessageEditable, 
    PlainMessage,
    PartnerApplicationMessage,
    ThreadEntryMessage, 
    SplitBillMessage,
    ApprovalMessage, 
    MessageTV,
)
