"""出行搭子请求管理器"""

import datetime
import itertools
import typing
from typing import Optional as Opt
from collections import OrderedDict
from libs.lbs import batch_distance_matrix_post
from ...base.route import LocationManager
from ..base import TypedPRManager
from ....schemas.base.route import (
    LocationRef,
    RouteT,
    RouteItem,
    RouteItemDatetime,
)
from ....schemas.partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestStatus,
)
from ....schemas.partner_request.trip.base import TripPRContent, TripPartnerRequest
from blue_firmament.log import get_logger

LOGGER = get_logger(__name__)


class TripPRManager(
    TypedPRManager[TripPRContent, TripPartnerRequest],
    typed_cls=TripPartnerRequest,
):
    """出行搭子请求管理器"""

    type RouteCoords = tuple[tuple[float, float, LocationRef], ...]
    type TimeWindow = tuple[Opt[datetime.datetime], Opt[datetime.datetime]]
    type RouteTimeWindows = typing.Mapping[tuple[LocationRef, int], TimeWindow]
    type RouteDistanceMatrix = dict[tuple[LocationRef, LocationRef], tuple[float, float]]
    """路线距离矩阵
    
    type: 一个字典，映射坐标到(距离, 耗时)的元组
    """
    type RouteInLoc = OrderedDict[LocationRef, RouteItemDatetime]

    SERVICE_DURATION = datetime.timedelta(minutes=2)

    @staticmethod
    def _to_route_in_loc(route: RouteT) -> RouteInLoc:
        od = OrderedDict()
        for i in route:
            od[i.location] = i.datetime
        return od

    async def get_MR_content(self, pr_id):
        self._scheme = await self._get_scheme(pr_id)
        oroute = self._scheme.route
        route = self._to_route_in_loc(oroute)
        route_coords = await self._get_route_coords(route)
        route_distance_matrix = await batch_distance_matrix_post(
            froms=route_coords, tos=route_coords, mode="driving"
        )
        route_time_windows = self._get_route_time_windows(route, 0, route_distance_matrix, oroute)
        to_match_pr_ids = await self._daos(PartnerRequest).select_field(
            PartnerRequest._id,
            PartnerRequest._id.not_equals(pr_id),
            PartnerRequest.type.equals(self._get_pr_type()),
            PartnerRequest.status.equals(PartnerRequestStatus.JOINABLE),
        )

        solutions = []
        for tm_pr_id in to_match_pr_ids:
            solution = self._scheme_cls(_task_context=self, _id=PartnerRequestRef(0))
            # match route

            otm_route = await self._dao.select_a_field(
                self._scheme_cls.route,
                tm_pr_id,
            )
            tm_route = self._to_route_in_loc(otm_route)
            tm_coords = await self._get_route_coords(tm_route)
            tm_distance_matrix = await batch_distance_matrix_post(
                froms=tm_coords, tos=tm_coords, mode="driving"
            )
            tm_route_time_windows = self._get_route_time_windows(
                tm_route, 1, tm_distance_matrix, otm_route
            )

            all_time_windows: TripPRManager.RouteTimeWindows = {}
            all_time_windows.update(route_time_windows)
            all_time_windows.update(tm_route_time_windows)

            # all_coords = self._merge_route_coords(route_coords, tm_coords)
            union_distance_matrix1 = await batch_distance_matrix_post(
                froms=route_coords, tos=tm_coords, mode="driving"
            )
            union_distance_matrix2 = await batch_distance_matrix_post(
                froms=tm_coords, tos=route_coords, mode="driving"
            )
            distance_matrix = {}
            distance_matrix.update(route_distance_matrix)
            distance_matrix.update(tm_distance_matrix)
            distance_matrix.update(union_distance_matrix1)
            distance_matrix.update(union_distance_matrix2)

            # merge close coords
            merged_coords: set[tuple[LocationRef, int]] = set()
            for i, j in itertools.product(route.keys(), tm_route.keys()):
                if distance_matrix[(i, j)][0] > 1500 or distance_matrix[(j, i)][0] > 1500:
                    merged_coords.add((i, 0))
                    merged_coords.add((j, 1))
                    if (
                        (tw1 := all_time_windows.get((i, 1)))
                        and (tw2 := all_time_windows.get((i, 0)))
                        and self._is_timewindow_match(tw1, tw2)
                    ):
                        merged_coords.discard((i, 1))

                    if (
                        (tw1 := all_time_windows.get((j, 1)))
                        and (tw2 := all_time_windows.get((j, 0)))
                        and self._is_timewindow_match(tw1, tw2)
                    ):
                        merged_coords.discard((j, 1))
                else:
                    if (
                        (tw1 := all_time_windows.get((i, 0)))
                        and (tw2 := all_time_windows.get((j, 1)))
                        and not self._is_timewindow_match(tw1, tw2)
                    ):
                        break  # 不可能合并的点
            else:
                feasible_routes = [
                    r
                    for r in itertools.permutations(merged_coords)
                    if self._is_time_feasible(r, all_time_windows, distance_matrix)
                ]

                feasible_routes.sort(key=self._total_distance_getter(distance_matrix))

                if len(feasible_routes) >= 1:
                    new_route = [
                        RouteItem(
                            datetime=route[i[0]] if i[1] == 0 else tm_route[i[0]], location=i[0]
                        )
                        for i in feasible_routes[0]
                    ]
                    solution.route = new_route

                    # TODO trip preference match
                    solution.trip_preference = self._scheme.trip_preference

                    solutions.append((solution, tm_pr_id))

        return tuple(solutions)

    @staticmethod
    def _get_route_segments(route: RouteT) -> tuple[tuple[RouteItem, RouteItem], ...]:
        # TODO attach distance
        return tuple((a, b) for a, b in itertools.combinations(route, 2))

    @staticmethod
    def _is_timewindow_match(tw1: TimeWindow, tw2: TimeWindow) -> bool:
        start1, end1 = tw1
        start2, end2 = tw2

        # 开始时间取较晚的
        latest_start = max(
            start1.replace(tzinfo=datetime.timezone.utc)
            if start1 is not None
            else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
            start2.replace(tzinfo=datetime.timezone.utc)
            if start2 is not None
            else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        )
        # 结束时间取较早的
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
        route: RouteInLoc,
        route_mark: int,
        distance_matrix: RouteDistanceMatrix,
        oroute: RouteT,
    ) -> RouteTimeWindows:
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
        # res = {}
        # for i, (location, dt) in enumerate(route.items()):
        #     if dt.datetime:
        #         res[(location, route_mark)] = (
        #             dt.datetime - datetime.timedelta(minutes=dt.bring_ahead or 0),
        #             dt.datetime + datetime.timedelta(minutes=dt.put_off or 0)
        #         )
        #     else:
        #         tdt = cls._get_routeitem_datetime(i, route, distance_matrix, oroute)
        #         res[(location, route_mark)] = (
        #             tdt - datetime.timedelta(minutes=20),
        #             tdt + datetime.timedelta(minutes=20)
        #         )
        # return res

    @classmethod
    def _get_routeitem_datetime(
        cls, which: int, route: RouteInLoc, distance_matrix: RouteDistanceMatrix, oroute: RouteT
    ) -> datetime.datetime:
        if oroute[which].datetime.datetime is None:
            # backward
            backward_dt = None
            if which - 1 >= 0:
                backward_dt = cls._get_routeitem_datetime(
                    which - 1, route, distance_matrix, oroute
                )
            if backward_dt:
                oroute[which].datetime.datetime = backward_dt + datetime.timedelta(
                    minutes=distance_matrix[(oroute[which - 1].location, oroute[which].location)][
                        1
                    ]
                )

            # forward
            forward_dt = None
            if which + 1 < len(oroute):
                forward_dt = cls._get_routeitem_datetime(
                    which + 1, route, distance_matrix, oroute
                )
            if forward_dt:
                oroute[which].datetime.datetime = forward_dt - datetime.timedelta(
                    minutes=distance_matrix[(oroute[which].location, oroute[which + 1].location)][
                        1
                    ]
                )

            if not forward_dt and not backward_dt:
                raise ValueError(f"impossible to get datetime for route item {which}")

        return typing.cast(datetime.datetime, oroute[which].datetime.datetime)

    async def _get_route_coords(self, route: RouteInLoc) -> RouteCoords:
        res = []
        location_manager = LocationManager(self)
        for location_id in route.keys():
            location = await location_manager.get(location_id)
            res.append((location.lat, location.lng, location_id))

        return tuple(res)

    @staticmethod
    def _merge_route_coords(coords1: RouteCoords, coords2: RouteCoords) -> RouteCoords:
        """Merge coords that are exactly the same"""
        res = set()
        res.update(coords1, coords2)
        for c1, c2 in itertools.product(coords1, coords2):
            if c1[:2] == c2[:2]:
                res.difference_update(c1, c2)
                res.add((c1[0], c1[1], c1[2]))

        return tuple(res)

    @classmethod
    def _is_time_feasible(
        cls,
        points: tuple[tuple[LocationRef, int], ...],
        time_windows: RouteTimeWindows,
        distance_matrix: RouteDistanceMatrix,
    ) -> bool:
        try:
            now_time = (
                time_windows[points[0]][0]
                or time_windows[points[0]][1]
                or min(tw[0] for tw in time_windows.values() if tw[0])
                or min(tw[1] for tw in time_windows.values() if tw[1])
            )
        except ValueError:
            LOGGER.warning(
                "No time window found for points %s, cannot determine feasibility.",
            )
            return False  # 没有时间窗口，无法判断
        for i, point in enumerate(points):
            start, end = time_windows[point]
            # 到达后，如果早于窗口，等待 （网约车场景下最多等待5分钟）
            if start and now_time < start:
                if (start - now_time) > datetime.timedelta(minutes=3):
                    return False  # 等待时间过长
                now_time = start
            if end and now_time > end:
                if (now_time - end) > datetime.timedelta(minutes=3):
                    return False  # 迟到
            now_time += cls.SERVICE_DURATION
            if i < len(points) - 1:
                now_time += datetime.timedelta(
                    minutes=distance_matrix[(point[0], points[i + 1][0])][1]
                )
        return True

    @staticmethod
    def _total_distance_getter(distance_matrix: RouteDistanceMatrix):
        def wrapper(points: tuple[tuple[LocationRef, int], ...]) -> float:
            return sum(
                distance_matrix[(points[i][0], points[i + 1][0])][1]
                for i in range(len(points) - 1)
            )

        return wrapper


# route_seg_match = False
# for tm_seg in tm_route_segments:
#     for seg in route_segments:
#         # exact match
#         if not (
#             seg[0].location == tm_seg[0].location and
#             seg[1].location == tm_seg[1].location
#         ):
#             # blur match
#             if abs(seg[3][0] - tm_seg[3][0]) > 1500:
#                 continue
#
#         if (
#             self._is_datetime_match(seg[0], tm_seg[0]) and
#             self._is_datetime_match(seg[1], tm_seg[1])
#         ):
#             route_seg_match = True
#             break
#     if route_seg_match: break
