"""分账模块管理器

Business logic for split bill operations using SQLModel and FastAPI patterns.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["SplitBillManager"]

import structlog
from typing import Optional as Opt

import sqlmodel

from core.engine import SessionLocal
from account.schemas import AccountRef
from ...schemas.split_bill import (
    SplitBill,
    SplitBillRef,
    SplitBillStatus,
)


logger = structlog.get_logger(__name__)


class SplitBillManager:
    """Split bill business logic manager.

    Provides methods for split bill operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, split_bill_id: SplitBillRef) -> Opt[SplitBill]:
        """Get a split bill by ID."""
        with SessionLocal() as db:
            return db.get(SplitBill, split_bill_id)

    @classmethod
    def is_editable(cls, split_bill_id: SplitBillRef) -> bool:
        """Check if split bill is editable."""
        split_bill = cls.get(split_bill_id)
        if not split_bill:
            return False
        return SplitBillStatus(split_bill.status) == SplitBillStatus.DRAFT

    @classmethod
    def is_contributable(cls, split_bill_id: SplitBillRef) -> bool:
        """Check if split bill is contributable."""
        split_bill = cls.get(split_bill_id)
        if not split_bill:
            return False
        status = SplitBillStatus(split_bill.status)
        return status in (SplitBillStatus.SUBMITTED, SplitBillStatus.CONTRIBUTING)

    @classmethod
    def get_mine(cls, account_id: AccountRef) -> list[SplitBillRef]:
        """Get split bills for an account."""
        with SessionLocal() as db:
            statement = sqlmodel.select(SplitBill.id).where(
                SplitBill.created_by == account_id
            )
            return list(db.exec(statement).all())

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a split bill."""
        # TODO: Implement when split bill schema is refactored
        logger.info("Create split bill")
        raise NotImplementedError("Split bill creation pending schema refactor")

    @classmethod
    def submit(cls, split_bill_id: SplitBillRef) -> Opt[SplitBill]:
        """Submit a split bill."""
        # TODO: Implement when split bill schema is refactored
        logger.info("Submit split bill", split_bill_id=split_bill_id)
        raise NotImplementedError("Split bill submit pending schema refactor")

    @classmethod
    def cancel(cls, split_bill_id: SplitBillRef) -> Opt[SplitBill]:
        """Cancel a split bill."""
        # TODO: Implement when split bill schema is refactored
        logger.info("Cancel split bill", split_bill_id=split_bill_id)
        raise NotImplementedError("Split bill cancel pending schema refactor")
