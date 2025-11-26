"""消息数据模型集合
"""

from .main import (
    PlainMessage, ThreadEntryMessage,
    PartnerApplicationMessage, ApprovalMessage
)

type MessageSchemeUnion = PlainMessage | ThreadEntryMessage | PartnerApplicationMessage | ApprovalMessage

