"""搭子（Partner）管理器"""

__all__ = ["PartnerManager"]

from typing import Optional as Opt
from blue_firmament import listen_to, Method
from blue_firmament.manager import CommonManager
from blue_firmament.task import TaskStatus
from ...schemas.partner_request import PartnerRequestRef
from ...schemas.partner_request.partner import Partner, PartnerRoleRef
from account.schemas import AccountRef


# TODO use CommonManager without p_key or separate p_key from CommonManager
class PartnerManager(
    CommonManager[Partner, int],
    scheme_cls=Partner,
    path_prefix="partner_request/{pr_id}/partner",
    manager_name="partner",
):
    """搭子管理器

    管理搭子请求中的搭子角色和扮演者
    """

    @listen_to(Method.GET, "")
    async def get_partners(self, pr_id: PartnerRequestRef) -> tuple[Partner, ...]:
        """获取搭子请求的所有搭子"""
        return await self._dao.select(
            Partner.partner_request.equals(pr_id),
        )

    @listen_to(Method.POST, "/{role_id}")
    async def create(
        self, pr_id: PartnerRequestRef, role_id: PartnerRoleRef, player: Opt[AccountRef] = None
    ) -> Partner:
        """创建搭子

        :param pr_id: 搭子请求 ID
        :param role_id: 角色 ID
        :param player: 扮演者
        """
        self._task_result.status = TaskStatus.CREATED
        return await self.insert(
            Partner(_task_context=self, partner_request=pr_id, role=role_id, player=player)
        )

    @listen_to(Method.DELETE, "/{role_id}")
    async def delete(self, pr_id: PartnerRequestRef, role_id: PartnerRoleRef) -> None:
        """删除（一个）搭子

        :param pr_id: 搭子请求 ID
        :param role_id: 搭子角色 ID
        """
        to_delete = await self._dao.select_one(
            Partner.partner_request.equals(pr_id),
            Partner.role.equals(role_id),
            Partner.player.is_(None),
            Partner.history.equals([]),
        )
        await self._dao.delete(to_delete=to_delete)

        self._task_result.status = TaskStatus.DELETED

    @listen_to(Method.PUT, "/{role_id}/disable")
    async def disable(self, pr_id: PartnerRequestRef, role_id: PartnerRoleRef) -> Partner:
        """禁用（一个）搭子

        不幂等（做不到）

        :param pr_id: 搭子请求 ID
        :param role_id: 搭子角色 ID
        """
        to_update = await self._dao.select_one(
            Partner.partner_request.equals(pr_id),
            Partner.role.equals(role_id),
            Partner.player.is_(None),
            Partner.disabled.is_(False),
        )
        to_update.disable()
        return await self._dao.update(to_update)

    async def play(
        self,
        role_id: PartnerRoleRef,
        pr_id: PartnerRequestRef,
        player: Opt[AccountRef] = None,
    ) -> Partner:
        """扮演

        :param role_id: 搭子角色 ID
        :param player: 扮演者账号 ID；默认为当前会话的账号 ID
        :param pr_id: 搭子请求 ID
        :raise Conflict: 搭子角色非空置时
        """
        partner = await self._dao.select_one(
            Partner.partner_request.equals(pr_id),
            Partner.role.equals(role_id),
        )
        partner.set_player(player or AccountRef(self._operator.id))
        await self._update_scheme(partner)

        await self._emit(".played", {"pr_id": pr_id})

        return self._scheme

    @listen_to(None, "/played", transporters=("event",))
    async def played(self, pr_id: PartnerRequestRef):
        """
        检查是否该搭子请求的所有搭子都已经被扮演，如果是的话则进入可执行
        """
        partner_players = await self._dao.select_field(
            Partner.player, Partner.partner_request.equals(pr_id)
        )
        if any(i is None for i in partner_players):
            return
        else:
            from .base import BasePRManager

            await BasePRManager(self).make_ready(pr_id=pr_id)
