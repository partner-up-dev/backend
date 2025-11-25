from .account import AccountRef
from dal import SupabaseAnonPostgrest
from main.schemas.partner_request import PartnerRequestRef
from blue_firmament.scheme import BaseScheme, FieldT, field


class MyLists(BaseScheme, dal=SupabaseAnonPostgrest, dal_path=("list", "account")):
    """我的列表

    不得不存储在账号中的列表
    """

    id: FieldT[AccountRef] = field(is_key=True)
    favorited_prs: FieldT[set[PartnerRequestRef]] = field(default_factory=set)
    """收藏的搭子请求"""
