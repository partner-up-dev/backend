"""Route and Location's Manager

Business logic for location operations using SQLModel and FastAPI patterns.
"""

__all__ = ["LocationManager"]

import structlog
from typing import Optional as Opt

from core.engine import SessionLocal
from ...schemas.base.route import Location, LocationRef


logger = structlog.get_logger(__name__)


class LocationManager:
    """Location business logic manager.

    Provides methods for location operations without BlueFirmament dependencies.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, location_id: LocationRef) -> Opt[Location]:
        """Get a location by ID."""
        with SessionLocal() as db:
            return db.get(Location, location_id)
