"""旅游搭子请求数据模型
"""

import typing
from blue_firmament.scheme import field, FieldT
from . import PartnerRequestL2Type, PRTypedContent, PartnerRequest


class TravelPRContent(PRTypedContent):

    pass

class TravelPartnerRequest(PartnerRequest, TravelPRContent):

    type: FieldT[PartnerRequestL2Type] = field(default=PartnerRequestL2Type.TRAVEL)
