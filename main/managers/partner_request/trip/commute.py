"""通勤搭子请求管理器

Business logic for commute partner request operations.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["CommutePRManager"]

import structlog
import sqlmodel
from typing import Optional as Opt

from .base import TripPRManager
from ....schemas.partner_request import PartnerRequestRef, PartnerRequest, PartnerRequestL2Type
from ....schemas.partner_request.trip.commute import CommutePRContent
from ....schemas.partner_request.trip.create import CommutePRCreate
from core.engine import SessionLocal
from account.schemas import AccountRef


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
    def create(
        cls,
        account_id: AccountRef,
        data: CommutePRCreate,
        db: Opt[sqlmodel.Session] = None,
    ) -> PartnerRequestRef:
        """Create a commute partner request.
        
        Creates both base PartnerRequest and CommutePRContent records.
        
        :param account_id: Account ID of the creator
        :param data: Create request data
        :param db: Optional database session
        :return: Created partner request ID
        """
        logger.info("Create commute PR", account_id=account_id)
        
        should_close_session = db is None
        if db is None:
            db = SessionLocal()
        
        try:
            # Create base partner request
            pr = PartnerRequest(
                type=PartnerRequestL2Type.COMMUTE.value,
                created_by=account_id,
                title=data.title,
                introduction=data.introduction,
            )
            db.add(pr)
            db.flush()  # Get the ID without committing
            
            # Create commute specific content
            content = CommutePRContent(
                id=pr.id,
                route=data.route,
                trip_preference=data.trip_preference,
                on_at=data.on_at,
                off_at=data.off_at,
                workdays=data.workdays if data.workdays else None,
            )
            db.add(content)
            db.commit()
            
            logger.info("Created commute PR", pr_id=pr.id)
            return pr.id
        except Exception as e:
            db.rollback()
            logger.error("Failed to create commute PR", error=str(e))
            raise
        finally:
            if should_close_session:
                db.close()

    @classmethod
    def update(cls, *args, **kwargs):
        """Update a commute partner request."""
        # TODO: Implement when commute schema is refactored
        logger.info("Update commute PR")
        raise NotImplementedError("Commute PR update pending schema refactor")
