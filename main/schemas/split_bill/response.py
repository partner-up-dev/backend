
from typing import Optional as Opt
from blue_firmament.scheme import BaseScheme
from .contribution import Contribution
from .main import SplitBill


class SplitBillV2CreateRes(SplitBill):
    contributions: list[Contribution]
    submitted: Opt[bool] = None

class SplitBillV1InitiateTransferRes(BaseScheme, proxy=False):
    package_info: str
