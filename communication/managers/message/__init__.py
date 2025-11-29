"""消息模块管理器包"""

__all__ = [
    "MessageManager",
    "ApprovalMessageManager",
]

from .main import MessageManager
from .approval import ApprovalMessageManager
