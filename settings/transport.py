from typing import Optional as Opt

from blue_firmament.scheme import FieldT, private_field
from blue_firmament.setting import EnvJsonSetting, make_setting_singleton


class TransportSetting(EnvJsonSetting):
    _setting_name: FieldT[str] = private_field(default="transport")
    _setting_path: FieldT[Opt[str]] = private_field(default="data/json/transport")
    _is_packaged: FieldT[bool] = private_field(default=False)

    http_host: str
    """HTTP 服务主机地址"""
    http_real_host: str
    """HTTP 服务外部主机（端口为 80/443）"""
    http_port: int
    """HTTP 服务端口；

    `docs https://git.hadream.ltd/anana/backend/gitlab-profile/wikis/home`_
    """


get_setting, set_setting = make_setting_singleton(TransportSetting.load())
