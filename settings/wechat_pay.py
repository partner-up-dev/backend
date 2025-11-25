"""微信支付配置"""

__all__ = ["get_setting", "set_setting"]

import os
from blue_firmament.setting import EnvJsonSetting, make_setting_singleton, private_field
from blue_firmament.scheme import FieldT, field


class WechatPaySetting(EnvJsonSetting):
    _setting_name = private_field("wechat_pay")
    _setting_path = private_field("data/json/wechat_pay")
    _is_packaged = private_field(False)

    mchid: str
    pri_key_path: str
    serial_no: str
    api_v3_key: FieldT[str] = field(
        default_factory=lambda: os.getenv("WECHAT_PAY_API_V3_KEY", "")
    )
    sign_type: str
    cert_dir: str


get_setting, set_setting = make_setting_singleton(WechatPaySetting.load())
