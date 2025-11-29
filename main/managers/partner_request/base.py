"""搭子请求模块的主要管理器

Business logic for partner request operations using SQLModel and FastAPI patterns.
"""

__all__ = ["PartnerRequestManager"]

import structlog
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from communication.managers.chat import ChatManager
from ...schemas.partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestStatus,
    PartnerRequestListType,
)
from ...schemas.partner_request.partner import Partner


logger = structlog.get_logger(__name__)


class PartnerRequestManager:
    """Partner request business logic manager.

    Provides methods for partner request operations without BlueFirmament dependencies.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, pr_id: PartnerRequestRef) -> Opt[PartnerRequest]:
        """Get a partner request by ID."""
        with SessionLocal() as db:
            return db.get(PartnerRequest, pr_id)

    @classmethod
    def is_admin(cls, pr_id: PartnerRequestRef, account_id: AccountRef) -> bool:
        """Check if account is admin of the partner request."""
        pr = cls.get(pr_id)
        if not pr:
            return False
        return pr.is_admin(account_id)

    @classmethod
    def get_list(
        cls,
        list_type: PartnerRequestListType,
        account_id: AccountRef,
    ) -> list[PartnerRequestRef]:
        """Get list of partner requests by type.

        :param list_type: Type of list to fetch
        :param account_id: Account ID to filter by
        :return: List of partner request IDs
        """
        result: list[PartnerRequestRef] = []

        with SessionLocal() as db:
            if list_type == PartnerRequestListType.ONGOING:
                statement = sqlmodel.select(PartnerRequest.id).where(
                    PartnerRequest.created_by == account_id,
                    PartnerRequest.status.in_(
                        [s.value for s in PartnerRequestStatus.ongoing_status()]
                    ),
                )
                results = db.exec(statement).all()
                result.extend(results)

            elif list_type == PartnerRequestListType.HISTORY:
                statement = sqlmodel.select(PartnerRequest.id).where(
                    PartnerRequest.created_by == account_id,
                    PartnerRequest.status.in_(
                        [s.value for s in PartnerRequestStatus.closed_status()]
                    ),
                )
                results = db.exec(statement).all()
                result.extend(results)

            elif list_type == PartnerRequestListType.DRAFT:
                statement = sqlmodel.select(PartnerRequest.id).where(
                    PartnerRequest.created_by == account_id,
                    PartnerRequest.status == PartnerRequestStatus.DRAFT.value,
                )
                results = db.exec(statement).all()
                result.extend(results)

        return result

    @classmethod
    def publish(cls, pr_id: PartnerRequestRef, account_id: AccountRef) -> Opt[PartnerRequest]:
        """Publish a partner request.

        :param pr_id: Partner request ID
        :param account_id: Account ID of the user
        :return: Updated partner request or None if not found/not allowed
        :raises ValueError: If not admin or wrong status
        """
        with SessionLocal() as db:
            pr = db.get(PartnerRequest, pr_id)
            if not pr:
                return None

            if not pr.is_admin(account_id):
                raise ValueError("Must be admin")

            if pr.status != PartnerRequestStatus.DRAFT.value:
                raise ValueError("Can only publish draft")

            # Create chat for the partner request
            chat = ChatManager.create_pr_chat(pr)

            pr.status = PartnerRequestStatus.JOINABLE.value
            pr.chat = chat.id
            pr.contract = 1  # TODO: Create contract when contract module is ready

            db.add(pr)
            db.commit()
            db.refresh(pr)
            return pr

    @classmethod
    def cancel(cls, pr_id: PartnerRequestRef, account_id: AccountRef) -> Opt[PartnerRequest]:
        """Cancel a partner request.

        :param pr_id: Partner request ID
        :param account_id: Account ID of the user
        :return: Updated partner request or None if not found/not allowed
        :raises ValueError: If not admin or wrong status
        """
        with SessionLocal() as db:
            pr = db.get(PartnerRequest, pr_id)
            if not pr:
                return None

            if not pr.is_admin(account_id):
                raise ValueError("Must be admin")

            if pr.status not in [
                PartnerRequestStatus.JOINABLE.value,
                PartnerRequestStatus.READY.value,
            ]:
                raise ValueError("Cannot cancel")

            pr.status = PartnerRequestStatus.CANCELLED.value
            db.add(pr)
            db.commit()
            db.refresh(pr)

            # Close the chat
            if pr.chat:
                ChatManager.close_chat(pr.chat)

            return pr

    @classmethod
    def next_status(
        cls, pr_id: PartnerRequestRef, account_id: AccountRef
    ) -> Opt[PartnerRequest]:
        """Move partner request to next status.

        :param pr_id: Partner request ID
        :param account_id: Account ID of the user
        :return: Updated partner request or None if not found/not allowed
        :raises ValueError: If not admin or no next status
        """
        with SessionLocal() as db:
            pr = db.get(PartnerRequest, pr_id)
            if not pr:
                return None

            if not pr.is_admin(account_id):
                raise ValueError("Must be admin")

            current_status = PartnerRequestStatus(pr.status)
            try:
                new_status = current_status.next()
                pr.status = new_status.value
                db.add(pr)
                db.commit()
                db.refresh(pr)
                return pr
            except ValueError:
                raise ValueError("No next status available")

    @classmethod
    def delete(cls, pr_id: PartnerRequestRef, account_id: AccountRef) -> bool:
        """Delete a partner request.

        :param pr_id: Partner request ID
        :param account_id: Account ID of the user
        :return: True if deleted, False if not found
        :raises ValueError: If not admin or not deletable
        """
        with SessionLocal() as db:
            pr = db.get(PartnerRequest, pr_id)
            if not pr:
                return False

            if not pr.is_admin(account_id):
                raise ValueError("Must be admin")

            if not pr.is_deletable():
                raise ValueError("Not deletable")

            db.delete(pr)
            db.commit()
            return True

    @classmethod
    def get_partners(cls, pr_id: PartnerRequestRef) -> list[Partner]:
        """Get partners for a partner request.

        :param pr_id: Partner request ID
        :return: List of partners
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Partner).where(Partner.partner_request == pr_id)
            return list(db.exec(statement).all())

    @classmethod
    def get_partners_account_ids(
        cls,
        pr_id: PartnerRequestRef,
        exclude_history: bool = True,
    ) -> set[AccountRef]:
        """Get account IDs of partners.

        :param pr_id: Partner request ID
        :param exclude_history: Whether to exclude historical players
        :return: Set of account IDs
        """
        import json

        account_ids: set[AccountRef] = set()
        partners = cls.get_partners(pr_id)

        for partner in partners:
            if partner.player is not None:
                account_ids.add(partner.player)
            if not exclude_history and partner.history:
                history = json.loads(partner.history) if partner.history else []
                account_ids.update(history)

        return account_ids
