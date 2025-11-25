
import os
from blue_firmament.data.settings import auth
from blue_firmament.scheme import FieldT, field

auth.SESSION_FIELDS_GETTER_DEFAULT["session_id"] = lambda payload: payload["session_id"]
auth.SESSION_FIELDS_GETTER_DEFAULT["roles"] = lambda payload: payload["role"]

class AuthSetting(auth.AuthSetting):

    jwt_secret_key: FieldT[str] = field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY", "")
    )
    jwt_allowed_audiences: tuple[str, ...] = ("authenticated", "anon", "service_role")

auth.set_setting(AuthSetting().load())

