"""搭子请求模块的主要管理器"""

__all__ = ["BasePRManager", "TypedPRManager"]

import asyncio
import typing
from typing import Optional as Opt

from blue_firmament.dal.query_components.operators import OrOperator
from blue_firmament.log import get_logger
from blue_firmament.task import TaskStatus
from blue_firmament.utils.enum_ import dump_enums
from account.schemas import AccountRef
from ...schemas.partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestL2Type,
    PartnerRequestEditable,
    PRTypedContent,
    PartnerRequestStatus,
    PartnerRequestListType,
    PRTypedUnion,
    PRTypedMapper,
    PartnerRoleRef,
    Partner,
)
from blue_firmament import listen_to, Method
from blue_firmament.manager import CommonManager
from communication.managers.chat import ChatManager

# from app.managers.contract import ContractManager
from blue_firmament.exceptions import (
    Conflict,
    Forbidden,
    ParamsInvalid,
    NotFound,
    InvalidStatusTransition,
)
from communication.managers.notification.channel_weixin import WXMPSubMessageManager
from communication.managers.notification.main import NotificationManager
from communication.schemas.notification import NotificationTask


logger = get_logger(__name__)


class BasePRManager(
    CommonManager[PartnerRequest, PartnerRequestRef],
    scheme_cls=PartnerRequest,
    path_prefix="partner_request",
    manager_name="partner_request",
):
    @listen_to(None, "/cancelled", transporters=("event",))
    async def close_chat(self, pr_id: PartnerRequestRef):
        """关闭群聊"""
        chat_id = await self._dao.select_a_field(PartnerRequest.chat, pr_id)
        await ChatManager(self).close(chat_id=chat_id)

    async def _is_admin(
        self,
        partner_request_id: PartnerRequestRef,
        account_id: Opt[AccountRef] = None,
    ) -> bool:
        """判断用户是否为搭子请求的管理员

        :param partner_request_id: 搭子请求 ID
        :param account_id: 账号 ID；默认为当前会话的账号 ID
        """
        account_id = AccountRef(account_id or self._operator.id)
        created_by = await self._dao.select_a_field(
            self._scheme_cls.created_by,
            int(partner_request_id),
        )
        return created_by == account_id

    async def _must_be_admin(
        self,
        pr_id: Opt[PartnerRequestRef] = None,
    ) -> None:
        """操作者必须为管理员

        :raises :class:`blue_firmament.exceptions.Forbidden`: 不是管理员时
        """
        pr = await self._get_scheme(_id=pr_id)
        if not pr.is_admin(AccountRef(self._operator.id)):
            raise Forbidden("must be admin")

    @listen_to(Method.GET, "/{pr_id}")
    async def get_full(self, pr_id: PartnerRequestRef) -> PRTypedUnion:
        """获取完整的搭子请求

        完整的搭子请求由搭子请求基类和搭子请求专业化内容组成，
        搭子请求专业化内容取决于搭子请求的类型。

        必须将该方法在基类实现，因为调用者不知道搭子请求的类型。

        :param pr_id: 搭子请求 ID
        :returns: （二级）搭子请求数据模型实例
        """
        base_pr = await self._get_scheme(_id=pr_id)

        from . import union

        typed_content = await union.PRManagerMapper[base_pr.type](self).get(_id=pr_id)

        return PRTypedMapper[base_pr.type].__from_parents__(base_pr, typed_content)

    async def get_partners_account_ids(
        self,
        pr_id: PartnerRequestRef,
        partners: Opt[typing.Iterable[Partner]] = None,
        exclude_history: bool = True,
    ) -> set[AccountRef]:
        """获取该搭子请求的搭子的账号ID列表

        :param pr_id: 搭子请求 ID
        :param partners: 搭子列表；如果提供了该参数，则忽略 pr_id
        :param exclude_history: 是否排除历史扮演搭子的账号
        """
        account_ids: set[AccountRef] = set()
        if not partners:
            partners = await self.get_partners(pr_id)
        for partner in partners:
            if partner.player is not None:
                account_ids.add(partner.player)
            if not exclude_history:
                account_ids.update(partner.history)
        return account_ids

    async def get_partners(
        self,
        pr_id: PartnerRequestRef,
    ) -> tuple[Partner, ...]:
        return await self._daos(Partner).select(Partner.partner_request.equals(pr_id))

    async def create(
        self, type_: PartnerRequestL2Type, body: PartnerRequestEditable
    ) -> PartnerRequest:
        """创建一般搭子请求"""
        return await self.insert(
            PartnerRequest(
                _id=PartnerRequestRef(0),
                type=type_,
                created_by=AccountRef(self._operator.id),
                **body.dump_to_dict(),
            )
        )

    async def update(
        self, body: PartnerRequestEditable, partner_request_id: Opt[PartnerRequestRef] = None
    ) -> PartnerRequest:
        """编辑搭子请求"""
        pr = await self._get_scheme(_id=partner_request_id)
        pr.title = body.title
        pr.introduction = body.introduction
        return await self._update_scheme(pr)

    @listen_to(Method.PUT, "/{pr_id}/publish")
    async def publish(self, pr_id: PartnerRequestRef) -> PartnerRequest:
        """发布搭子请求

        Behavior
        --------
        1. 校验前置条件
        2. 更新数据
        3. 告知搭子发现系统

        校验前置条件
        ^^^^^^^^^^^^
        - 状态为草稿
            - 否则抛出 :meth:`blue_firmament.exceptions.DuplicateOrConflict`

        更新数据
        ^^^^^^^^^
        - 更新 created_at
        - 更新 status 为 waiting_for_partners
        - 创建群聊
        - 创建契约
        - 更新到数据库（失败则删除群聊与契约）

        """
        pr = await self._get_scheme(_id=pr_id)

        # 条件
        # 权限
        await self._must_be_admin()

        # create chat
        chat = await ChatManager(self).create_pr_chat(partner_request=pr)

        # [contract]
        # TODO when contract finished
        # contract = await ContractManager(self).create(partner_request=pr)

        pr.status = pr.status.to_joinable()
        pr.created_at = self._scheme_cls.created_at.default_value  # reset created_at
        pr.chat = chat._id
        # pr.contract = contract._id
        pr.contract = 1

        # update to db
        try:
            pr = await self._dao.update(pr)
        except Exception as e:
            # TODO cleanup
            raise e

        await self._emit(".published", parameters={"pr_id": pr_id})

        return pr

    @listen_to(Method.GET, "/list/{list_type}")
    async def get_list(
        self, list_type: PartnerRequestListType, account_id: Opt[AccountRef] = None
    ) -> set[PartnerRequestRef]:
        """获取搭子请求列表

        :param list_type: 列表类型
        :param account_id: 指定账号，默认为当前会话的
        """
        result: set[PartnerRequestRef] = set()
        account_id = AccountRef(account_id or self._operator.id)

        if list_type == PartnerRequestListType.FAVORITE:
            # TODO redirect response
            pass
        elif list_type == PartnerRequestListType.ONGOING:
            try:
                c1 = await self._dao.select_field(
                    self._scheme_cls._id,
                    self._scheme_cls.created_by.equals(account_id),
                    self._scheme_cls.status.in_(
                        dump_enums(PartnerRequestStatus.ongoing_status())
                    ),
                )
                """我创建的，状态是进行中的搭子请求"""
                result.update(c1)

                c2 = await self._daos(Partner).select_field(
                    Partner.partner_request,
                    OrOperator(
                        Partner.player.equals(account_id),
                        Partner.history.contains(account_id),
                    ),
                    self._scheme_cls.status.in_(
                        dump_enums(PartnerRequestStatus.ongoing_status())
                    ),
                )
                """我是搭子的，状态是进行中的搭子请求"""
                result.update(c2)
            except NotFound:
                pass
        elif list_type == PartnerRequestListType.HISTORY:
            try:
                c1 = await self._dao.select_field(
                    self._scheme_cls._id,
                    self._scheme_cls.created_by.equals(account_id),
                    self._scheme_cls.status.in_(dump_enums(PartnerRequestStatus.closed_status())),
                )
                """我创建的，状态是已关闭的搭子请求"""
                result.update(c1)
                c2 = await self._daos(Partner).select_field(
                    Partner.partner_request,
                    OrOperator(
                        Partner.player.equals(account_id),
                        Partner.history.contains(account_id),
                    ),
                    self._scheme_cls.status.in_(dump_enums(PartnerRequestStatus.closed_status())),
                )
                """我是搭子的，状态是已关闭的搭子请求"""
                result.update(c2)
            except NotFound:
                pass
        elif list_type == PartnerRequestListType.DRAFT:
            try:
                return set(
                    await self._dao.select_field(
                        self._scheme_cls._id,
                        self._scheme_cls.created_by.equals(account_id),
                        self._scheme_cls.status.equals(PartnerRequestStatus.DRAFT),
                    )
                )
            except NotFound:
                pass
        else:
            raise ParamsInvalid("list_type not supported")

        return result

    @listen_to(Method.PUT, "/{pr_id}/cancel")
    async def cancel(self, pr_id: PartnerRequestRef) -> PartnerRequest:
        """取消搭子请求

        Docs
        ----
        `SIYUAN <siyuan://blocks/20250501143251-dt4epx8>`_
        """
        self._scheme = await self.get(pr_id)
        await self._must_be_admin()
        self._scheme.status = self._scheme.status.to_cancelled()
        await self._update_scheme()
        await self._emit(".cancelled", parameters={"pr_id": self._scheme._id})
        # TODO 在幂等请求中发出事件？发出事件不是幂等的 -> 事件处理器需要自行确保幂等性
        return self._scheme

    @listen_to(Method.DELETE, "/{partner_request_id}")
    async def delete(self, partner_request_id: PartnerRequestRef) -> None:
        """删除搭子请求

        Docs
        ----
        `SIYUAN <siyuan://blocks/20250501215338-2c7vpx5>`_
        """
        self._scheme = await self._get_scheme(partner_request_id)
        await self._must_be_admin()
        if not self._scheme.is_deletable():
            raise Conflict("not deletable")
        await super().delete()
        self._task_result.status = TaskStatus.DELETED

    @listen_to(Method.PUT, "/{pr_id}/status/next")
    async def next_status(self, pr_id: PartnerRequestRef) -> PartnerRequestStatus:
        """切换到下一个状态

        :param pr_id: 搭子请求 ID
        :returns: 下一个状态
        """
        pr_status = await self._dao.select_one(
            self._scheme_cls.status,
            pr_id,
        )
        new_status = None

        await self._must_be_admin()

        if pr_status == PartnerRequestStatus.JOINABLE:
            new_status = PartnerRequestStatus.READY
        elif pr_status == PartnerRequestStatus.READY:
            # TODO need TypedManager allow
            new_status = PartnerRequestStatus.PERFORMING
        elif pr_status == PartnerRequestStatus.PERFORMING:
            # TODO need TypedManager allow
            new_status = PartnerRequestStatus.SETTLING

        if new_status is not None:
            return await self._dao.update(
                (self._scheme_cls.status, new_status),  # type: ignore
                pr_id,
            )

        raise InvalidStatusTransition("PR", self._scheme.status, new_status)

    type SimplePartner = tuple[PartnerRoleRef, Opt[AccountRef]]

    @listen_to(None, "/published", transporters=("event",))
    async def match_internally(self, pr_id: PartnerRequestRef):
        """搭子请求内发现

        :issues: #102
        """
        self._scheme = await self._get_scheme(pr_id)

        solutions: list[
            tuple[tuple[PRTypedContent, list[BasePRManager.SimplePartner]], PartnerRequestRef]
        ] = []

        # content MR solutions
        from . import union

        typed_manager = union.PRManagerMapper[self._scheme.type](self)
        content_MR_solutions = await typed_manager.get_MR_content(pr_id)

        # partner MR solutions
        partners = await self.get_partners(pr_id)
        for content_solution, tm_pr_id in content_MR_solutions:
            partner_solution: list[BasePRManager.SimplePartner] = [
                (partner.role, partner.player) for partner in partners
            ]
            tm_partners = await self.get_partners(tm_pr_id)
            for tm_partner in tm_partners:
                try:
                    free = partner_solution.index((tm_partner.role, None))
                except ValueError:
                    continue  # not match (not free or no such role)
                else:
                    partner_solution[free] = (tm_partner.role, tm_partner.player)

            solutions.append(((content_solution, partner_solution), tm_pr_id))

        # create draft MR
        from ...schemas.partner_request.merge import PRMergeRequest
        from .merge import PRMergeSubmitNotification

        await asyncio.gather(
            *tuple(
                self._daos(PRMergeRequest).insert(
                    PRMergeRequest(
                        _task_context=self,
                        created_by=AccountRef(self._scheme.created_by),
                        froms=(pr_id, tm_pr_id),
                        n_created_by=AccountRef(self._scheme.created_by),
                        n_partners=solution[1],
                        n_typed_content=solution[0],
                    )
                )
                for solution, tm_pr_id in solutions
            )
        )

        # notify
        await NotificationManager(self).send(
            NotificationTask(
                to=tuple(self._scheme.created_by),
                channel=WXMPSubMessageManager,
                content=PRMergeSubmitNotification(
                    from_pr=self._scheme._id, to_merge_pr_count=len(solutions)
                ),
            )
        )

    async def is_mergeable(self, pr_id: Opt[PartnerRequestRef] = None):
        self._scheme = await self._get_scheme(pr_id)
        return self._scheme.is_mergeable()

    async def _merged(self, pr_id: Opt[PartnerRequestRef] = None) -> None:
        self._scheme = await self._get_scheme(pr_id)
        self._scheme.status = self._scheme.status.to_merged()
        await self._daos(Partner).update(
            {Partner.player: None}, Partner.partner_request.equals(self._scheme._id)
        )

    async def make_ready(self, pr_id: Opt[PartnerRequestRef] = None):
        self._scheme = await self._get_scheme(pr_id)
        self._scheme.status = self._scheme.status.to_ready()
        await self._update_scheme()


PRTypedTV = typing.TypeVar("PRTypedTV", bound=PRTypedUnion)
PRTypedContentTV = typing.TypeVar("PRTypedContentTV", bound=PRTypedContent)


class TypedPRManager(
    # TODO inherit TypedManager, CommonManager
    CommonManager[PRTypedContentTV, PartnerRequestRef],
    typing.Generic[PRTypedContentTV, PRTypedTV],
    scheme_cls=PartnerRequest,
    manager_name="typed_pr",
):
    """专业化搭子请求管理器

    - 每个类型的创建接口都会被注册到该类的 create 方法
    """

    def __init_subclass__(cls, typed_cls: type[PRTypedTV], **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__typed_cls__ = typed_cls

    def __init__(self, task_context) -> None:
        super().__init__(task_context)
        self._basem = BasePRManager(task_context)
        """基础搭子请求管理器"""

    def _get_pr_type(self) -> PartnerRequestL2Type:
        return self.__typed_cls__.type.default_value

    async def _create(
        self, base_editable: PartnerRequestEditable, content: PRTypedContentTV
    ) -> PRTypedTV:
        """创建专业化搭子请求"""
        base_pr = await self._basem.create(type_=self._get_pr_type(), body=base_editable)
        content._id = base_pr._id

        try:
            content = await self.insert(content)
        except Exception as e:
            # TODO transaction
            # FIXME 奇妙消失的 _scheme
            await self._basem.delete(base_pr._id)
            raise e

        self._task_result.status = TaskStatus.CREATED
        return self.__typed_cls__.__from_parents__(base_pr, content)

    async def _update(
        self,
        pr_id: PartnerRequestRef,
        base_editable: PartnerRequestEditable,
        content: PRTypedContentTV,
    ) -> PRTypedTV:
        """更新专业化搭子请求"""
        base_pr = await self._basem.update(body=base_editable, partner_request_id=pr_id)
        content = await self._update_scheme(content)

        return self.__typed_cls__.__from_parents__(base_pr, content)

    async def get_MR_content(
        self, pr_id: PartnerRequestRef
    ) -> tuple[tuple[PRTypedContentTV, PartnerRequestRef], ...]:
        """内发现可合并搭子请求的内容合并方案"""
        raise NotImplementedError
