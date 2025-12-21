"""网约车搭子请求管理器

Business logic for ride-hailing partner request operations.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["RideHailingPRManager"]

import structlog
import sqlmodel
from typing import Optional as Opt

from .base import TripPRManager
from ....schemas.partner_request import PartnerRequestRef, PartnerRequest, PartnerRequestL2Type
from ....schemas.partner_request.trip.ride_hailing import RideHailingPRContent
from ....schemas.partner_request.trip.create import RideHailingPRCreate
from core.engine import SessionLocal
from account.schemas import AccountRef


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
    def create(
        cls,
        account_id: AccountRef,
        data: RideHailingPRCreate,
        db: Opt[sqlmodel.Session] = None,
    ) -> PartnerRequestRef:
        """Create a ride-hailing partner request.
        
        Creates both base PartnerRequest and RideHailingPRContent records.
        
        :param account_id: Account ID of the creator
        :param data: Create request data
        :param db: Optional database session
        :return: Created partner request ID
        """
        logger.info("Create ride-hailing PR", account_id=account_id)
        
        if db is None:
            db = SessionLocal()
            should_close_session = True
        else:
            should_close_session = False
        
        try:
            # Create base partner request
            pr = PartnerRequest(
                type=PartnerRequestL2Type.RIDE_HAILING.value,
                created_by=account_id,
                title=data.title,
                introduction=data.introduction,
            )
            db.add(pr)
            db.flush()  # Get the ID without committing
            
            # Create ride-hailing specific content
            content = RideHailingPRContent(
                id=pr.id,
                route=data.route,
                trip_preference=data.trip_preference,
                ride_hailing_preference=data.ride_hailing_preference,
            )
            db.add(content)
            db.commit()
            
            logger.info("Created ride-hailing PR", pr_id=pr.id)
            return pr.id
        except Exception as e:
            db.rollback()
            logger.error("Failed to create ride-hailing PR", error=str(e))
            raise
        finally:
            if should_close_session:
                db.close()

    @classmethod
    def update(cls, *args, **kwargs):
        """Update a ride-hailing partner request."""
        # TODO: Implement when ride-hailing schema is refactored
        logger.info("Update ride-hailing PR")
        raise NotImplementedError("Ride-hailing PR update pending schema refactor")
