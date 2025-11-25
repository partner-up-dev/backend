"""
desc: Route and Location's Manager
"""

# typing
# from app.managers import BaseManager
from backend_common.managers import BaseManager

# logging
from backend_common.libs.logs import top_logger
logger = top_logger.getChild("RouteManager")

# schemas
from app.schemas.base.route import Location


class LocationManager(BaseManager, Location):

    _DB_SCHEMA = "public"
    _TABLE = "location"
    _IS_HASH = True
    _ID_TYPE = "hash"
