"""Partner schema."""

import typing
import sqlalchemy
import sqlmodel
from typing import Optional as Opt, NewType

from account.schemas import AccountRef

if typing.TYPE_CHECKING:
    pass


PartnerRoleRef = NewType("PartnerRoleRef", int)


class Partner(sqlmodel.SQLModel, table=True):
    """搭子 database model."""
    __tablename__ = "partner"  # type: ignore
    __table_args__ = {"schema": "partner_request"}

    id: Opt[int] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.Integer, primary_key=True, autoincrement=True),
        default=None,
    )
    partner_request: int = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    )
    """搭子请求 ID"""
    role: int = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    )
    """搭子角色 ID"""
    player: Opt[AccountRef] = sqlmodel.Field(default=None)
    """当前扮演该搭子的用户 ID"""
    history: Opt[str] = sqlmodel.Field(default=None)  # JSON array of AccountRef
    """历史扮演该搭子角色的用户 ID 列表"""
    disabled: bool = sqlmodel.Field(default=False)
    """是否禁用"""

    def is_free(self) -> bool:
        """是否空置"""
        return not self.player

    def set_player(self, player: AccountRef, safe: bool = False) -> Opt[AccountRef]:
        """设置该搭子的扮演者"""
        if self.disabled:
            if safe:
                return None
            raise ValueError("partner is disabled")
        if not self.is_free():
            if safe:
                return None
            raise ValueError("partner is not free")
        self.player = player
        return self.player

    def disable(self):
        """禁用该搭子"""
        if not self.is_free():
            raise ValueError("partner is not free")
        self.disabled = True
