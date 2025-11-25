__all__ = ["get_setting", "set_setting"]

import os
import typing
from blue_firmament.setting import Setting, make_setting_singleton


class WeixinAppCredential(typing.TypedDict):
    appid: str
    secret: str


class WeixinSetting(Setting):
    credentials: dict[str, WeixinAppCredential] = {
        "partner_up_wxmp": {
            "appid": "wx7674f72ff1eb49e6",
            "secret": os.getenv("WEIXIN_PARTNER_UP_WXMP_SECRET", ""),
        },
        "partner_up_wxsa": {
            "appid": os.getenv("WEIXIN_PARTNER_UP_WXSA_APPID", ""),
            "secret": os.getenv("WEIXIN_PARTNER_UP_WXSA_SECRET", ""),
        },
    }


get_setting, set_setting = make_setting_singleton(WeixinSetting())
