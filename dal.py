__all__ = ["SupabaseAnonPostgrest", "SupabaseServPostgrest", "DefaultRedis"]


from blue_firmament.dal.postgrest import PostgrestDAL
from settings.dal import get_setting as get_dal_setting


class SupabaseAnonPostgrest(
    PostgrestDAL,
    url=get_dal_setting().postgrest_url,
    apikey=get_dal_setting().anon_key,
    default_schema="public",
    default_table="profile",
): ...


class SupabaseServPostgrest(
    PostgrestDAL,
    url=get_dal_setting().postgrest_url,
    apikey=get_dal_setting().serv_key,
    default_schema="public",
    default_table="profile",
): ...


from blue_firmament.dal.redis import RedisDAL
from settings.redis import get_setting as get_redis_setting


class DefaultRedis(
    RedisDAL,
    host=get_redis_setting().host,
    port=get_redis_setting().port,
    password=get_redis_setting().password,
    db=get_redis_setting().db,
):
    pass
