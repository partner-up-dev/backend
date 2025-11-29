"""通勤搭子请求管理器

Business logic for commute partner request operations.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["CommutePRManager"]

import structlog

from .base import TripPRManager
from ....schemas.partner_request import PartnerRequestRef


logger = structlog.get_logger(__name__)


class CommutePRManager(TripPRManager):
    """通勤搭子请求管理器

    Provides methods for commute partner request operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, pr_id: PartnerRequestRef):
        """Get a commute partner request by ID."""
        # TODO: Implement when commute schema is refactored
        logger.info("Get commute PR", pr_id=pr_id)
        pass

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a commute partner request."""
        # TODO: Implement when commute schema is refactored
        logger.info("Create commute PR")
        raise NotImplementedError("Commute PR creation pending schema refactor")

    @classmethod
    def update(cls, *args, **kwargs):
        """Update a commute partner request."""
        # TODO: Implement when commute schema is refactored
        logger.info("Update commute PR")
        raise NotImplementedError("Commute PR update pending schema refactor")
