"""网约车搭子请求管理器

Business logic for ride-hailing partner request operations.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["RideHailingPRManager"]

import structlog

from .base import TripPRManager
from ....schemas.partner_request import PartnerRequestRef


logger = structlog.get_logger(__name__)


class RideHailingPRManager(TripPRManager):
    """网约车搭子请求管理器

    Provides methods for ride-hailing partner request operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, pr_id: PartnerRequestRef):
        """Get a ride-hailing partner request by ID."""
        # TODO: Implement when ride-hailing schema is refactored
        logger.info("Get ride-hailing PR", pr_id=pr_id)
        pass

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a ride-hailing partner request."""
        # TODO: Implement when ride-hailing schema is refactored
        logger.info("Create ride-hailing PR")
        raise NotImplementedError("Ride-hailing PR creation pending schema refactor")

    @classmethod
    def update(cls, *args, **kwargs):
        """Update a ride-hailing partner request."""
        # TODO: Implement when ride-hailing schema is refactored
        logger.info("Update ride-hailing PR")
        raise NotImplementedError("Ride-hailing PR update pending schema refactor")
