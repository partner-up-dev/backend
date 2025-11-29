
from typing import Optional as Opt
from pydantic import BaseModel


class SplitBillV2CreateRes(BaseModel):
    """Response for split bill creation."""
    submitted: Opt[bool] = None


class SplitBillV1InitiateTransferRes(BaseModel):
    """Response for split bill transfer initiation."""
    package_info: str
