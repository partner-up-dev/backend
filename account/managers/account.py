__all__ = ["SupabaseAuth", "AccountIdentityManager", "BaseProfileManager"]

import typing
from typing import Annotated as Anno, Literal as Lit, Optional as Opt
from blue_firmament import listen_to
from blue_firmament.exceptions import Forbidden, NotImplemented, NotFound
from blue_firmament.log import get_logger
from blue_firmament.manager import CommonManager, PresetHandlerConfig

from ..schemas.manager import (
    V1SetPIIBody,
    PIIType,
    V1SetPIIVerProvider,
)
from ..schemas.account import (
    AccountConfig,
    BaseProfile,
    AccountRef,
    AccountProfileSimple,
    BaseProfileEditable,
    GeoProfile,
)
from gotrue import AsyncGoTrueClient
from settings.supabase import get_setting as get_supabase_setting
from libs.weixin import WXMP_MP_API


LOGGER = get_logger(__name__)


class SupabaseAuth:
    @classmethod
    def get_anon_client(cls) -> AsyncGoTrueClient:
        return AsyncGoTrueClient(
            url=get_supabase_setting().url + "/auth/v1",
            headers={
                "apiKey": get_supabase_setting().anon_key,
                "authorization": f"Bearer {get_supabase_setting().anon_key}",
            },
        )

    @classmethod
    def get_authenticated_client(cls, access_token: str) -> AsyncGoTrueClient:
        return AsyncGoTrueClient(
            url=get_supabase_setting().url + "/auth/v1",
            headers={
                "apiKey": get_supabase_setting().anon_key,
                "authorization": f"Bearer {access_token}",
            },
        )

    @classmethod
    def get_serv_client(cls) -> AsyncGoTrueClient:
        return AsyncGoTrueClient(
            url=get_supabase_setting().url + "/auth/v1",
            headers={
                "apiKey": get_supabase_setting().serv_key,
                "authorization": f"Bearer {get_supabase_setting().serv_key}",
            },
        )


class AccountIdentityManager(CommonManager, path_prefix="account"):
    @listen_to("GET", "/identity/{account_id}/{pii_type}")
    async def get_pii(
        self,
        pii_type: PIIType,
        account_id: AccountRef,
    ):
        """获取PII"""
        if self._operator.id != account_id:
            if "service_role" not in self._operator.roles:
                raise Forbidden("must be service role to get other's PII")

        supabase_auth = SupabaseAuth.get_serv_client()
        res = await supabase_auth.admin.get_user_by_id(account_id)

        if pii_type == PIIType.PHONE:
            if res.user.phone:
                return res.user.phone
            else:
                raise NotFound
        elif pii_type == PIIType.EMAIL:
            if res.user.email:
                return res.user.email
            else:
                raise NotFound

    @listen_to("PUT", "/identity/{account_id}/{pii_type}")
    async def set_pii(
        self,
        account_id: AccountRef,
        pii_type: PIIType,
        verification_provider: V1SetPIIVerProvider,
        body: V1SetPIIBody,
    ) -> typing.Any:
        """修改PII

        :param account_id: 账号 ID
        :param pii_type: PII 类型
        :param verification_provider: PII验证器

        :docs: https://app.apifox.com/link/project/4406548/apis/api-241112998?branchId=5433542
        """
        if self._operator.id != account_id:
            if "service_role" not in self._operator.roles:
                raise Forbidden("must be service role to set other's PII")

        if verification_provider == V1SetPIIVerProvider.WXMP_MP:
            if pii_type == PIIType.PHONE:
                new_pii = await WXMP_MP_API(self).get_phone_number(body.code)
                supabase_auth = SupabaseAuth.get_serv_client()
                res = await supabase_auth.admin.update_user_by_id(
                    account_id, {"phone_confirm": True, "phone": new_pii}
                )
                return res.user.phone

            raise NotImplemented("PIIType %s" % pii_type)

        raise NotImplemented("verification provider %s" % verification_provider)


class BaseProfileManager(
    CommonManager[BaseProfile, AccountRef],
    scheme_cls=BaseProfile,
    path_prefix="account/profile/base",
    preset_handler_config=PresetHandlerConfig(put=True, editable=BaseProfileEditable),
):
    @listen_to("GET", "/{account_id}")
    async def get(self, account_id: AccountRef) -> BaseProfile:
        self._scheme = await self._get_scheme(account_id)
        account_config = await self._daos(AccountConfig).select_one(account_id)
        if self._scheme.id != self._operator.id:
            return account_config.filter_public(self._scheme)
        return self._scheme

    @listen_to("GET", "/{account_id}/simple")
    async def get_simple(self, account_id: AccountRef) -> AccountProfileSimple:
        self._scheme = await self._get_scheme(account_id)
        return AccountProfileSimple(**self._scheme)
