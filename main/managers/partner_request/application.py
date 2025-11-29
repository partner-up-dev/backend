"""搭子申请管理器

Business logic for partner application operations using SQLModel and FastAPI patterns.
"""

__all__ = ["PartnerApplicationManager"]

import typing
import json
import structlog
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from communication.managers.chat import ChatManager
from ...schemas.partner_request import (
    PartnerApplication,
    PartnerApplicationRef,
    PartnerApplicationStatus,
    PartnerRoleRef,
    PartnerRequestRef,
    SubPartnerApplication,
)
from .base import PartnerRequestManager
from .partner import PartnerManager


logger = structlog.get_logger(__name__)


class PartnerApplicationManager:
    """Partner application business logic manager.

    Provides methods for partner application operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, application_id: PartnerApplicationRef) -> Opt[PartnerApplication]:
        """Get a partner application by ID."""
        with SessionLocal() as db:
            return db.get(PartnerApplication, application_id)

    @classmethod
    def create(
        cls,
        partner_request_id: PartnerRequestRef,
        applicant: AccountRef,
        sub_applications: typing.List[SubPartnerApplication],
    ) -> Opt[PartnerApplication]:
        """Create a partner application.

        :param partner_request_id: Partner request ID
        :param applicant: Applicant account ID
        :param sub_applications: List of sub-applications
        :return: Created application or None
        :raises ValueError: If PR chat is None
        """
        pr = PartnerRequestManager.get(partner_request_id)
        if not pr:
            raise ValueError("Partner request not found")

        if pr.chat is None:
            raise ValueError("Partner request chat is None")

        # Create application chat
        application = PartnerApplication(
            applicant=applicant,
            partner_request=partner_request_id,
            sub_applications=json.dumps([s.model_dump() for s in sub_applications]),
            chat=0,  # Will be updated after creating chat
        )

        # Create application chat linked to PR chat
        application_chat = ChatManager.create_partner_application_chat(application, pr.chat)

        with SessionLocal() as db:
            application.chat = application_chat.id
            db.add(application)
            db.commit()
            db.refresh(application)
            return application

    @classmethod
    def get_mine(cls, account_id: AccountRef) -> list[PartnerApplication]:
        """Get applications for an account.

        :param account_id: Account ID
        :return: List of applications
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(PartnerApplication).where(
                PartnerApplication.applicant == account_id
            )
            return list(db.exec(statement).all())

    @classmethod
    def withdraw(
        cls,
        application_id: PartnerApplicationRef,
        reason: str,
    ) -> Opt[PartnerApplication]:
        """Withdraw an application.

        :param application_id: Application ID
        :param reason: Withdrawal reason
        :return: Updated application or None
        :raises ValueError: If application is not open
        """
        with SessionLocal() as db:
            application = db.get(PartnerApplication, application_id)
            if not application:
                return None

            status = PartnerApplicationStatus(application.status)
            if not status.is_open():
                raise ValueError("Application is not open")

            application.status = PartnerApplicationStatus.WITHDRAWN.value
            application.eclose_reason = reason
            db.add(application)
            db.commit()
            db.refresh(application)

            # Close the application chat
            ChatManager.close_chat(application.chat)

            return application

    @classmethod
    def approve(
        cls,
        application_id: PartnerApplicationRef,
        admin_id: AccountRef,
        role_ids: list[PartnerRoleRef],
    ) -> Opt[PartnerApplication]:
        """Approve an application.

        :param application_id: Application ID
        :param admin_id: Admin account ID (must be PR admin)
        :param role_ids: List of role IDs to assign
        :return: Updated application or None
        :raises ValueError: If not admin, application not open, or no roles available
        """
        with SessionLocal() as db:
            application = db.get(PartnerApplication, application_id)
            if not application:
                return None

            # Check admin permission
            pr = PartnerRequestManager.get(application.partner_request)
            if not pr or not pr.is_admin(admin_id):
                raise ValueError("Must be admin")

            status = PartnerApplicationStatus(application.status)
            if not status.is_open():
                raise ValueError("Application is not open")

            # Try to assign roles
            played = 0
            for role_id in role_ids:
                try:
                    PartnerManager.play(
                        pr_id=application.partner_request,
                        role_id=role_id,
                        player=application.applicant,
                    )
                    played += 1
                except ValueError:
                    logger.warning("Partner not free anymore, skip", partner=role_id)
                    continue

            if played == 0:
                raise ValueError("No role is available for this application")

            application.status = PartnerApplicationStatus.APPROVED.value
            db.add(application)
            db.commit()
            db.refresh(application)
            return application

    @classmethod
    def reject(
        cls,
        application_id: PartnerApplicationRef,
        admin_id: AccountRef,
        reason: str,
    ) -> Opt[PartnerApplication]:
        """Reject an application.

        :param application_id: Application ID
        :param admin_id: Admin account ID (must be PR admin)
        :param reason: Rejection reason
        :return: Updated application or None
        :raises ValueError: If not admin or application not open
        """
        with SessionLocal() as db:
            application = db.get(PartnerApplication, application_id)
            if not application:
                return None

            # Check admin permission
            pr = PartnerRequestManager.get(application.partner_request)
            if not pr or not pr.is_admin(admin_id):
                raise ValueError("Must be admin")

            status = PartnerApplicationStatus(application.status)
            if not status.is_open():
                raise ValueError("Application is not open")

            application.status = PartnerApplicationStatus.REJECTED.value
            application.eclose_reason = reason
            db.add(application)
            db.commit()
            db.refresh(application)
            return application
