"""搭子（Partner）管理器

Business logic for partner operations using SQLModel and FastAPI patterns.
"""

__all__ = ["PartnerManager"]

import structlog
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from ...schemas.partner_request import PartnerRequestRef
from ...schemas.partner_request.partner import Partner, PartnerRoleRef


logger = structlog.get_logger(__name__)


class PartnerManager:
    """Partner business logic manager.

    Manages partner roles and players in partner requests.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get_partners(cls, pr_id: PartnerRequestRef) -> list[Partner]:
        """Get all partners for a partner request.

        :param pr_id: Partner request ID
        :return: List of partners
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Partner).where(Partner.partner_request == pr_id)
            return list(db.exec(statement).all())

    @classmethod
    def create(
        cls,
        pr_id: PartnerRequestRef,
        role_id: PartnerRoleRef,
        player: Opt[AccountRef] = None,
    ) -> Partner:
        """Create a partner.

        :param pr_id: Partner request ID
        :param role_id: Role ID
        :param player: Optional player account ID
        :return: Created partner
        """
        with SessionLocal() as db:
            partner = Partner(
                partner_request=pr_id,
                role=role_id,
                player=player,
            )
            db.add(partner)
            db.commit()
            db.refresh(partner)
            return partner

    @classmethod
    def delete(cls, pr_id: PartnerRequestRef, role_id: PartnerRoleRef) -> bool:
        """Delete a partner.

        :param pr_id: Partner request ID
        :param role_id: Role ID
        :return: True if deleted
        :raises ValueError: If partner not found or has player/history
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Partner).where(
                Partner.partner_request == pr_id,
                Partner.role == role_id,
                Partner.player.is_(None),
            )
            partner = db.exec(statement).first()
            if not partner:
                raise ValueError("Partner not found or has player")

            db.delete(partner)
            db.commit()
            return True

    @classmethod
    def disable(cls, pr_id: PartnerRequestRef, role_id: PartnerRoleRef) -> Opt[Partner]:
        """Disable a partner.

        :param pr_id: Partner request ID
        :param role_id: Role ID
        :return: Updated partner or None
        :raises ValueError: If partner not found or not free
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Partner).where(
                Partner.partner_request == pr_id,
                Partner.role == role_id,
                Partner.player.is_(None),
                Partner.disabled.is_(False),
            )
            partner = db.exec(statement).first()
            if not partner:
                raise ValueError("Partner not found or not free")

            partner.disable()
            db.add(partner)
            db.commit()
            db.refresh(partner)
            return partner

    @classmethod
    def play(
        cls,
        pr_id: PartnerRequestRef,
        role_id: PartnerRoleRef,
        player: AccountRef,
    ) -> Opt[Partner]:
        """Assign a player to a partner role.

        :param pr_id: Partner request ID
        :param role_id: Role ID
        :param player: Player account ID
        :return: Updated partner or None
        :raises ValueError: If partner not found or not free
        """
        with SessionLocal() as db:
            statement = sqlmodel.select(Partner).where(
                Partner.partner_request == pr_id,
                Partner.role == role_id,
            )
            partner = db.exec(statement).first()
            if not partner:
                raise ValueError("Partner not found")

            partner.set_player(player)
            db.add(partner)
            db.commit()
            db.refresh(partner)
            return partner

    @classmethod
    def check_all_played(cls, pr_id: PartnerRequestRef) -> bool:
        """Check if all partners have players.

        :param pr_id: Partner request ID
        :return: True if all partners have players
        """
        partners = cls.get_partners(pr_id)
        return all(p.player is not None for p in partners)
