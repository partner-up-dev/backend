import os
from blue_firmament.setting import EnvJsonSetting, make_setting_singleton, private_field
from blue_firmament.scheme import FieldT, field


class SupabaseSetting(EnvJsonSetting):
    _setting_name = private_field("supabase")
    _is_packaged = private_field(False)
    _setting_path = private_field("data/json/supabase")

    url: str
    """Supabase URL"""
    serv_key: FieldT[str] = field(default_factory=lambda: os.getenv("SUPABASE_SERV_KEY", ""))
    """Supabase Service Key"""
    anon_key: FieldT[str] = field(default_factory=lambda: os.getenv("SUPABASE_ANON_KEY", ""))
    """Supabase Anon Key"""


get_setting, set_setting = make_setting_singleton(SupabaseSetting.load())
