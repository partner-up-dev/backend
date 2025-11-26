import aiohttp
import typing
from typing import Literal as Lit
from blue_firmament.log import get_logger
from settings.lbs import get_setting

LOGGER = get_logger(__name__)
BATCH_DISTANCE_MATRIX_URL = "https://apis.map.qq.com/ws/distance/v1/matrix"


TV = typing.TypeVar("TV")


async def batch_distance_matrix_post(
    froms: tuple[tuple[float, float, TV], ...],
    tos: tuple[tuple[float, float, TV], ...],
    mode: Lit["driving", "walking", "bicycling"] = "driving",
) -> dict[tuple[TV, TV], tuple[float, float]]:
    """批量距离计算（矩阵）

    :param froms: start points coordinates, represent coordinates in tuple[lat,lng]
    :param tos: end points coordinates, represent coordinates in tuple[lat,lng]
    :param mode: driving, walking, bicycling
    :returns: A dict, mapping a pair of `from:to` to distance,duration.

    TODO error handling
    """
    params = {
        "key": get_setting().apikey,
        "mode": mode,
        "from": ";".join(f"{lat},{lng}" for lat, lng, _ in froms),
        "to": ";".join(f"{lat},{lng}" for lat, lng, _ in tos),
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BATCH_DISTANCE_MATRIX_URL, data=params) as response:
            response.raise_for_status()
            result = (await response.json())["result"]["rows"]
            res = {}

            for i in range(len(result)):
                for j in range(len(result[i]["elements"])):
                    tmp = result[i]["elements"][j]
                    res[(froms[i][2], tos[j][2])] = (tmp["distance"], int(tmp["duration"] / 60))
            return res
