"""消息数据模型集合
"""

import typing
from typing import Optional as Opt, Annotated as Anno, Literal as Lit
import main
from .main import (
    MessageContentUnion,
    PlainMessage, ThreadEntryMessage,
    PartnerApplicationMessage, ApprovalMessage
)

type MessageSchemeUnion = typing.Union[
    PlainMessage,
    ThreadEntryMessage,
    PartnerApplicationMessage,
    ApprovalMessage
]

