import typing
from typing import Optional as Opt

from blue_firmament.exceptions import Conflict
from blue_firmament.scheme import field, FieldT
from blue_firmament.task.context import SoCommonTC
from dal import SupabaseAnonPostgrest
from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    from .base import PartnerRequestRef


PartnerRoleRef = typing.NewType("PartnerRoleRef", int)


class PartnerRole(
    SoCommonTC,
    proxy=True,
    dal=SupabaseAnonPostgrest,
    dal_path=("partner_role", "partner_request"),
):
    pass  # TODO


class Partner(
    SoCommonTC, proxy=True, dal=SupabaseAnonPostgrest, dal_path=("partner", "partner_request")
):
    """搭子"""

    _id: FieldT[int] = field(default=0, is_natural_key=True)
    partner_request: FieldT["PartnerRequestRef"]
    """搭子请求 ID
    """
    role: FieldT[PartnerRoleRef]
    """搭子角色 ID
    """
    player: FieldT[Opt[AccountRef]] = None
    """当前扮演该搭子的用户 ID
    """
    history: FieldT[list[AccountRef]] = field(default_factory=list)
    """历史扮演该搭子角色的用户 ID 列表
    """
    disabled: FieldT[bool] = False
    """是否禁用
    
    禁用则不能被扮演
    """

    def is_free(self) -> bool:
        """是否空置"""
        return not self.player

    def set_player(self, player: AccountRef, safe: bool = False) -> Opt[AccountRef]:
        """设置该搭子的扮演者

        :raise Conflict: 非空且 unsafe
        :returns: player 如果成功，否则 None
        """
        if self.disabled:
            if safe:
                return None
            raise Conflict("partner is disabled")
        if not self.is_free():
            if safe:
                return None
            raise Conflict("partner is not free")
        self.player = player
        return self.player

    def disable(self):
        """禁用该搭子

        :raise Conflict: 如果搭子已经被扮演
        """
        if not self.is_free():
            raise Conflict("partner is not free")
        self.disabled = True
