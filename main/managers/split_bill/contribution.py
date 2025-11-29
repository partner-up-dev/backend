"""贡献记录管理器

Business logic for contribution operations using SQLModel and FastAPI patterns.
This is a simplified manager that removes BlueFirmament dependencies.
"""

__all__ = ["ContributionManager"]

import structlog
from typing import Optional as Opt


from account.schemas import AccountRef
from ...schemas.split_bill import (
    Contribution,
    SplitBillRef,
)


logger = structlog.get_logger(__name__)


class ContributionManager:
    """Contribution business logic manager.

    Provides methods for contribution operations.
    Uses SQLModel sessions directly.
    """

    @classmethod
    def get(cls, split_bill_id: SplitBillRef, contributor: AccountRef) -> Opt[Contribution]:
        """Get a contribution by composite key."""
        # TODO: Implement when contribution schema is refactored
        logger.info("Get contribution", split_bill_id=split_bill_id, contributor=contributor)
        return None

    @classmethod
    def create(cls, *args, **kwargs):
        """Create a contribution."""
        # TODO: Implement when contribution schema is refactored
        logger.info("Create contribution")
        raise NotImplementedError("Contribution creation pending schema refactor")

    @classmethod
    def contribute(cls, *args, **kwargs):
        """Request contribution."""
        # TODO: Implement when contribution schema is refactored
        logger.info("Contribute")
        raise NotImplementedError("Contribution pending schema refactor")

    @classmethod
    def is_contributed(
        cls,
        split_bill_id: SplitBillRef,
        contributor: AccountRef,
    ) -> bool:
        """Check if contribution is contributed."""
        contribution = cls.get(split_bill_id, contributor)
        if not contribution:
            return False
        # TODO: Implement when contribution schema is refactored
        return False

    @classmethod
    def refund(cls, *args, **kwargs):
        """Refund contribution."""
        # TODO: Implement when contribution schema is refactored
        logger.info("Refund contribution")
        raise NotImplementedError("Contribution refund pending schema refactor")
