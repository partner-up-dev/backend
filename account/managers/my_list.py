import typing
from typing import Annotated as Anno, Literal as Lit, Optional as Opt
from blue_firmament import listen_to
from blue_firmament.manager import CommonManager

from ..schemas.account import AccountRef
from ..schemas.my_list import MyLists


class MyListManager(
    CommonManager[MyLists, AccountRef], scheme_cls=MyLists, path_prefix="account/my_list"
):
    @listen_to("GET", "/{account_id}/{list_id}")
    def get_list(
        self,
        account_id: AccountRef,
        list_id: str,
    ):
        """获取我的列表"""
        return self.get_a_field(field=MyLists.__fields__[list_id], _id=account_id)

    @listen_to("POST", "/{account_id}/{list_id}")
    def add_to_list(
        self, account_id: AccountRef, list_id: str, body: tuple[typing.Any, ...], **kwargs
    ):
        """插入元素到我的列表"""
        return self.insert_item(
            field=MyLists.__fields__[list_id], _id=account_id, values=body, **kwargs
        )

    @listen_to("DELETE", "/{account_id}/{list_id}")
    def delete_from_list(
        self,
        account_id: AccountRef,
        list_id: str,
        body: tuple[typing.Any, ...],
    ):
        """从我的列表删除元素"""
        return self.delete_item(field=MyLists.__fields__[list_id], _id=account_id, values=body)
