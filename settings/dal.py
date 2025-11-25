"""DAL Settings"""

import os
from blue_firmament.setting import EnvJsonSetting, make_setting_singleton, private_field
from blue_firmament.scheme import FieldT, field


class DALSetting(EnvJsonSetting):
    _setting_name = private_field("dal")
    _is_packaged = private_field(False)
    _setting_path = private_field("data/json/dal")

    postgrest_url: str
    serv_key: FieldT[str] = field(default_factory=lambda: os.getenv("DAL_SERV_KEY", ""))
    anon_key: FieldT[str] = field(default_factory=lambda: os.getenv("DAL_ANON_KEY", ""))


get_setting, set_setting = make_setting_singleton(DALSetting.load())
