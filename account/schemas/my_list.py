"""My Lists Schema for Account."""

import typing
import sqlmodel
from typing import Optional as Opt
from .account import AccountRef
import sqlalchemy


PartnerRequestRef: typing.TypeAlias = int


class MyLists(sqlmodel.SQLModel, table=True):
    """我的列表

    不得不存储在账号中的列表
    """

    __tablename__ = "list"  # type: ignore
    __table_args__ = {"schema": "account"}

    id: AccountRef = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.UUID, primary_key=True),
    )
    favorited_prs: Opt[str] = sqlmodel.Field(default=None)  # JSON array of PartnerRequestRef
    """收藏的搭子请求"""
