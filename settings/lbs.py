import os
from blue_firmament.setting import Setting, make_setting_singleton
from blue_firmament.scheme import FieldT, field


class LBSSetting(Setting):
    apikey: FieldT[str] = field(default_factory=lambda: os.getenv("LBS_APIKEY", ""))


get_setting, set_setting = make_setting_singleton(LBSSetting())
