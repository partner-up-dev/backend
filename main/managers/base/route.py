"""Route and Location's Manager"""

from blue_firmament.manager import CommonManager, PresetHandlerConfig
from blue_firmament.log import get_logger
from ...schemas.base.route import Location, LocationRef

LOGGER = get_logger(__name__)


class LocationManager(
    CommonManager[Location, LocationRef],
    manager_name="location",
    scheme_cls=Location,
    path_prefix="base/location",
    preset_handler_config=PresetHandlerConfig(get=True),
): ...
