"""核心服务的数据模型

This module re-exports the core models used throughout the `main` service.
It provides convenience imports so other packages can import models from
`main.schemas` directly, for example:

        from main.schemas import PartnerRequest, SplitBill, Transaction, Currency

Only stable core models are exported here — refer to the subpackages for
domain-specific models if needed.
"""

from .base import (
    Currency,
    Weekday,
    Navigation,
    NavigationMethod,
    Gender,
    MBTI,
)
from .base.route import Location, RouteItem, LocationRef, RouteItemDatetime
from .base.label import Label, LabelRef, Labels, LabelsDetail
from .base.requirement import (
    Requirement,
    RequirementType,
    RequirementRef,
    Requirements,
    RequirementsDetail,
)

from .partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestStatus,
    PartnerRequestType,
    PartnerRequestL2Type,
    PRTypedContent,
    PartnerRequestEditable,
    PartnerRequestListType,
    PartnerApplication,
    PartnerApplicationStatus,
    SubPartnerApplication,
    PartnerApplicationRef,
    Partner,
    PartnerRoleRef,
    RideHailingPRContent,
    CommutePRContent,
)

from .split_bill import (
    SplitBill,
    SplitBillRef,
    SplitBillStatus,
    SplitBillType,
    SplitBillCancelReason,
    SplitBillCreate,
    SplitBillEditable,
    Contribution,
    ContributionStatus,
    ContributeOn,
    ContributionEditable,
    ContributionKeys,
    ContributionCreate,
)

from .payment.base import (
    Transaction,
    TransactionStatus,
    TransactionType,
    TransferScene,
    PaymentPlatform,
)

from .payment.wallet import (
    Wallet,
    WalletIssuer,
)

__all__ = [
    # base
    "Currency",
    "Weekday",
    "Navigation",
    "NavigationMethod",
    "Gender",
    "MBTI",
    "Location",
    "LocationRef",
    "RouteItem",
    "RouteItemDatetime",
    "Label",
    "LabelRef",
    "Labels",
    "LabelsDetail",
    "Requirement",
    "RequirementType",
    "RequirementRef",
    "Requirements",
    "RequirementsDetail",
    # partner_request
    "PartnerRequest",
    "PartnerRequestRef",
    "PartnerRequestStatus",
    "PartnerRequestType",
    "PartnerRequestL2Type",
    "PRTypedContent",
    "PartnerRequestEditable",
    "PartnerRequestListType",
    "PartnerApplication",
    "PartnerApplicationStatus",
    "SubPartnerApplication",
    "PartnerApplicationRef",
    "Partner",
    "PartnerRoleRef",
    "RideHailingPRContent",
    "CommutePRContent",
    # split_bill
    "SplitBill",
    "SplitBillRef",
    "SplitBillStatus",
    "SplitBillType",
    "SplitBillCancelReason",
    "SplitBillCreate",
    "SplitBillEditable",
    "Contribution",
    "ContributionStatus",
    "ContributeOn",
    "ContributionEditable",
    "ContributionKeys",
    "ContributionCreate",
    # payment
    "Transaction",
    "TransactionStatus",
    "TransactionType",
    "TransferScene",
    "PaymentPlatform",
    "Wallet",
    "WalletIssuer",
]
