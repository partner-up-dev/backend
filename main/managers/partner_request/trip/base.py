"""出行搭子请求管理器

Business logic for trip partner request operations.
This is a simplified manager that removes BlueFirmament dependencies.
"""

import datetime
import typing
import structlog
from typing import Optional as Opt
from collections import OrderedDict

from ....schemas.base.route import (
    LocationRef,
    RouteItem,
    RouteItemDatetime,
)


logger = structlog.get_logger(__name__)

RouteT = list[RouteItem]


class TripPRManager:
    """Trip partner request manager.

    Provides methods for trip-related partner request operations.
    """

    type RouteCoords = tuple[tuple[float, float, LocationRef], ...]
    type TimeWindow = tuple[Opt[datetime.datetime], Opt[datetime.datetime]]
    type RouteTimeWindows = typing.Mapping[tuple[LocationRef, int], TimeWindow]
    type RouteDistanceMatrix = dict[tuple[LocationRef, LocationRef], tuple[float, float]]
    type RouteInLoc = OrderedDict[LocationRef, RouteItemDatetime]

    SERVICE_DURATION = datetime.timedelta(minutes=2)

    @staticmethod
    def _to_route_in_loc(route: RouteT) -> "TripPRManager.RouteInLoc":
        od = OrderedDict()
        for i in route:
            od[i.location] = i.datetime
        return od

    @staticmethod
    def _is_timewindow_match(
        tw1: "TripPRManager.TimeWindow", tw2: "TripPRManager.TimeWindow"
    ) -> bool:
        start1, end1 = tw1
        start2, end2 = tw2

        latest_start = max(
            start1.replace(tzinfo=datetime.timezone.utc)
            if start1 is not None
            else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
            start2.replace(tzinfo=datetime.timezone.utc)
            if start2 is not None
            else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        )
        earliest_end = min(
            end1.replace(tzinfo=datetime.timezone.utc)
            if end1 is not None
            else datetime.datetime.max.replace(tzinfo=datetime.timezone.utc),
            end2.replace(tzinfo=datetime.timezone.utc)
            if end2 is not None
            else datetime.datetime.max.replace(tzinfo=datetime.timezone.utc),
        )

        return latest_start <= earliest_end

    @classmethod
    def _get_route_time_windows(
        cls,
        route: "TripPRManager.RouteInLoc",
        route_mark: int,
        distance_matrix: "TripPRManager.RouteDistanceMatrix",
        oroute: RouteT,
    ) -> "TripPRManager.RouteTimeWindows":
        return {
            (location, route_mark): (
                dt.datetime - datetime.timedelta(minutes=dt.bring_ahead)
                if dt.bring_ahead is not None
                else None,
                dt.datetime + datetime.timedelta(minutes=dt.put_off)
                if dt.put_off is not None
                else None,
            )
            if dt.datetime
            else (None, None)
            for location, dt in route.items()
        }

    @classmethod
    def _is_time_feasible(
        cls,
        points: tuple[tuple[LocationRef, int], ...],
        time_windows: "TripPRManager.RouteTimeWindows",
        distance_matrix: "TripPRManager.RouteDistanceMatrix",
    ) -> bool:
        try:
            now_time = (
                time_windows[points[0]][0]
                or time_windows[points[0]][1]
                or min(tw[0] for tw in time_windows.values() if tw[0])
                or min(tw[1] for tw in time_windows.values() if tw[1])
            )
        except ValueError:
            logger.warning("No time window found for points, cannot determine feasibility")
            return False
        for i, point in enumerate(points):
            start, end = time_windows[point]
            if start and now_time < start:
                if (start - now_time) > datetime.timedelta(minutes=3):
                    return False
                now_time = start
            if end and now_time > end:
                if (now_time - end) > datetime.timedelta(minutes=3):
                    return False
            now_time += cls.SERVICE_DURATION
            if i < len(points) - 1:
                now_time += datetime.timedelta(
                    minutes=distance_matrix[(point[0], points[i + 1][0])][1]
                )
        return True

    @staticmethod
    def _total_distance_getter(
        distance_matrix: "TripPRManager.RouteDistanceMatrix"
    ):
        def wrapper(points: tuple[tuple[LocationRef, int], ...]) -> float:
            return sum(
                distance_matrix[(points[i][0], points[i + 1][0])][1]
                for i in range(len(points) - 1)
            )
        return wrapper
