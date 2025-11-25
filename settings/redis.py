import os
from blue_firmament.setting import EnvJsonSetting, make_setting_singleton, private_field
from blue_firmament.scheme import FieldT, field


class RedisSetting(EnvJsonSetting):
    _setting_name = private_field("redis")
    _is_packaged = private_field(False)
    _setting_path = private_field("data/json/redis")

    host: str
    """Redis主机地址"""
    port: int
    """Redis端口"""
    password: FieldT[str] = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    """Redis密码"""
    db: int


get_setting, set_setting = make_setting_singleton(RedisSetting.load())
