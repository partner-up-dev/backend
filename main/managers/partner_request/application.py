"""搭子申请管理器"""

import typing
from typing import Annotated as Anno
from typing import Literal as Lit
from typing import Optional as Opt

from blue_firmament import Method, listen_to
from blue_firmament.exceptions import Conflict, Forbidden, ParamsInvalid
from blue_firmament.manager import CommonManager, PresetHandlerConfig
from blue_firmament.scheme import ListConverter
from blue_firmament.task import TaskStatus
from account.schemas import AccountRef
from communication.schemas.chat import ChatRef
from ...schemas.partner_request import (
    PartnerApplication,
    PartnerApplicationRef,
    PartnerRoleRef,
    PartnerRequestRef,
    SubPartnerApplication,
)

from communication.managers.chat import ChatManager
from communication.managers.message.main import (
    PartnerApplicationMessageManager,
)
from .base import BasePRManager
from .partner import PartnerManager


class PartnerApplicationManager(
    CommonManager[PartnerApplication, PartnerApplicationRef],
    scheme_cls=PartnerApplication,
    path_prefix=BasePRManager.__path_prefix__ + "/application",
    manager_name="application",
    preset_handler_config=PresetHandlerConfig(get=True),
):
    @listen_to(Method.POST, "")
    async def create(
        self, partner_request_id: PartnerRequestRef, body: typing.List[SubPartnerApplication]
    ) -> PartnerApplication:
        """创建搭子申请

        TODO 事务性

        Docs
        ----
        - `APIFOX <https://app.apifox.com/link/project/4406548/apis/api-176452036>`_
        - `DOC <siyuan://blocks/20250429155614-t3cesu2>`_
        """
        pr = await BasePRManager(self).get(partner_request_id)
        application = PartnerApplication(
            _task_context=self,
            _id=PartnerApplicationRef(0),
            applicant=AccountRef(self._operator.id),
            partner_request=partner_request_id,
            sub_applications=body,
            chat=ChatRef(0),
        )

        if pr.chat is not None:
            # create application chat
            # link application chat to partner_request chat
            application_chat = await ChatManager(self).create_partner_application_chat(
                application=application, pr_chat_id=pr.chat
            )

            # create application
            application.chat = application_chat._id
            application = await self._dao.insert(application)

            # sent application message
            await PartnerApplicationMessageManager(self).send(
                application=application, application_chat_id=application_chat._id
            )

            self._task_result.status = TaskStatus.CREATED
            return application

        raise ParamsInvalid("pr chat is None")

    @listen_to(Method.GET, "/mine")
    async def get_mine(self) -> tuple[PartnerApplication]:
        """获取我的搭子申请

        Docs
        ----
        - `SIYUAN <siyuan://blocks/20250430233324-hgjelvb>`_
        """
        return await self._dao.select(
            PartnerApplication.applicant.equals(self._session.operator.id),
        )

    @listen_to(Method.PUT, "/{application_id}/withdraw")
    async def withdraw(
        self,
        application_id: PartnerApplicationRef,
        body: str,
    ) -> PartnerApplication:
        """撤回申请

        :param application_id: 搭子申请 ID
        :param body: 取消原因

        Docs
        ----
        - `SIYUAN <siyuan://blocks/20250429214653-f9k1dyk>`_
        """
        application = await self._get_scheme(application_id)

        # 更新数据
        application.withdraw(reason=body)
        await self._update_scheme(application)

        # 关闭搭子申请群聊 非主要
        await ChatManager(self).close(application.chat)

        return application

    @listen_to(Method.PUT, "/{application_id}/approve")
    async def approve(
        self,
        application_id: PartnerApplicationRef,
        body: Anno[list[PartnerRoleRef], ListConverter(PartnerRoleRef, min_len=1)],
    ) -> PartnerApplication:
        """同意搭子申请

        1. 更新搭子申请状态
        2. 更新搭子请求搭子列表，将同意申请人扮演的搭子角色扮演者设置为申请人

        Docs
        ----
        `SIYUAN <siyuan://blocks/20250429235823-ud2mvnc>`_
        """
        self._scheme = await self._get_scheme(_id=application_id)
        partner_manager = PartnerManager(self)

        await BasePRManager(self)._must_be_admin(self._scheme.partner_request)

        played = 0
        for role_id in body:
            try:
                await partner_manager.play(
                    pr_id=self._scheme.partner_request,
                    role_id=role_id,
                    player=self._scheme.applicant,
                )
            except Conflict:
                self._logger.warning("partner not free anymore, skip", partner=role_id)
                continue
            else:
                played += 1

        if played == 0:
            raise Conflict("No role is available for this application")

        self._scheme.approve()
        await self._update_scheme()

        await self._emit(".approved", parameters={"application_id": self._scheme._id})
        # TODO 检查其它搭子请求是否过期 BGTASK

        return self._scheme

    @listen_to(Method.PUT, "/{application_id}/reject")
    async def reject(
        self, application_id: PartnerApplicationRef, body: str
    ) -> PartnerApplication:
        """驳回搭子申请

        Docs
        ----
        `SIYUAN <siyuan://blocks/20250429235836-q6e3sdj>`_
        """
        self._scheme = await self._get_scheme(application_id)
        await BasePRManager(self)._must_be_admin(self._scheme.partner_request)

        self._scheme.reject(reason=body)
        await self._update_scheme()

        self._emit(".rejected", parameters={"application_id": self._scheme._id})

        return self._scheme
