import jwt
import time
import uuid
from blue_firmament import listen_to
from blue_firmament.data.settings.auth import get_setting as get_auth_setting
from blue_firmament.exceptions import NotFound
from blue_firmament.manager import CommonManager
from libs.weixin import WXMP_MP_API, WXMP_SA_API
from .account import BaseProfileManager, SupabaseAuth
from ..schemas.account import AccountRef, BaseProfile
from ..schemas.manager import V2WXMPLoginBody
from ..schemas.wxmp import WXMPAccount, WXMPClientType


class WXMPAccountManager(
    CommonManager[WXMPAccount, AccountRef], scheme_cls=WXMPAccount, path_prefix="account/wxmp"
):
    """微信公众平台帐号管理器"""

    @listen_to("POST", "/{client_type}/login")
    async def login(self, client_type: WXMPClientType, body: V2WXMPLoginBody) -> BaseProfile:
        """微信公众平台登录

        通过微信公众号平台的OpenID登录时，创建的是临时帐号，在其它客户端（如移动端、网页端）是无法登录的

        :param client_type: 客户端类型
        :param body: 其它参数

        Behaviour
        -----------
        - 根据客户端，查找已注册的账号
        - 如果没找到，则注册新账号
        - 如果账号存在，尝试链接不同的服务提供商
        - 登录之，而后
            - 设置账号资料到响应体中
            - 设置响应头 `Authorization`
            - 设置Cookie `refresh_token`
        """
        # get openid
        unionid = self._scheme_cls.weixin_unionid.default_value
        # openid = "oK1ud682MkihwAGeUu2hyX4ZcxqI"  # TEMP
        if client_type == WXMPClientType.MINIPROGRAM:
            openid, unionid = await WXMP_MP_API(self).get_openid(body.code)
        elif client_type == WXMPClientType.SERVICE_ACCOUNT:
            openid, unionid = await WXMP_SA_API(self).get_openid(body.code)
        else:
            raise ValueError("Unsupported WXMP Client Type %s" % client_type)

        openid_field = self._scheme_cls.get_openid_field(client_type)
        try:
            # 使用 OpenID 查找记录
            self._scheme = await self._dao.select_one(openid_field.equals(openid))
        except NotFound:
            try:
                # 使用 UnionID 查找记录
                self._scheme = await self._dao.select_one(
                    self._scheme_cls.weixin_unionid.equals(unionid)
                )
            except NotFound:
                # 没有记录，创建临时帐号、创建资料、记录OpenID
                supa_auth_client = SupabaseAuth.get_anon_client()
                signin_res = await supa_auth_client.sign_in_anonymously()
                if signin_res.user is None or signin_res.session is None:
                    # TODO Service Unavailable
                    raise RuntimeError
                else:
                    account = signin_res.user
                    session = signin_res.session
                self._scheme = WXMPAccount(id=account.id, weixin_unionid=unionid)
                self._scheme.set_openid(client_type, openid)
                await self.insert()
                profile = await BaseProfileManager(self).insert(BaseProfile(id=account.id))
                self._task_result.metadata.authorization = ("Bearer", session.access_token)
                self._task_result.metadata.state["refresh_token"] = session.refresh_token
                return profile
            else:
                self._scheme[openid_field] = openid
                await self._update_scheme()
        else:
            # 保存 UnionID 如果没有
            if not self._scheme.weixin_unionid and unionid:
                self._scheme.weixin_unionid = unionid
                await self._update_scheme()

        # 手动生成 JWT （临时帐号无法在 Supabase Auth 重新登录，直到绑定一个PII）
        payload = {
            "sub": self._scheme.id,
            "iss": "anana-backend-main/account",
            "session_id": uuid.uuid4().hex,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60 * 60,
            "aud": "authenticated",
            "role": "authenticated",
            "is_anonymous": True,
        }
        access_token = jwt.PyJWT().encode(
            payload,
            key=get_auth_setting().jwt_secret_key,
            algorithm=get_auth_setting().jwt_algorithms[0],
        )
        self._task_result.metadata.authorization = "Bearer", access_token
        profile = await BaseProfileManager(self).get(self._scheme.id)

        # return account profile
        return profile
