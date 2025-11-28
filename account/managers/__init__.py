"""帐号服务的管理器"""

from .account import SupabaseAuth, get_account_profile, get_account_profile_simple
from .my_list import get_my_lists, add_to_favorited_prs, remove_from_favorited_prs

__all__ = [
    "SupabaseAuth",
    "get_account_profile",
    "get_account_profile_simple",
    "get_my_lists",
    "add_to_favorited_prs",
    "remove_from_favorited_prs",
]
