"""搭子请求模块的数据模型"""

__all__ = [
    # Base models
    "PartnerRequest",
    "PartnerRequestRef",
    "PartnerRequestStatus",
    "PartnerRequestType",
    "PartnerRequestL2Type",
    "PRTypedContent",
    "PartnerRequestEditable",
    "PartnerRequestListType",
    # Application models
    "PartnerApplication",
    "PartnerApplicationStatus",
    "SubPartnerApplication",
    "PartnerApplicationRef",
]

from .base import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestStatus,
    PartnerRequestType,
    PartnerRequestL2Type,
    PRTypedContent,
    PartnerRequestEditable,
    PartnerRequestListType,
)
from .trip import (
    CommutePRContent,
    RideHailingPRContent,
)
from .partner import PartnerRoleRef, Partner

from .application import (
    PartnerApplication,
    PartnerApplicationStatus,
    SubPartnerApplication,
    PartnerApplicationRef,
)
