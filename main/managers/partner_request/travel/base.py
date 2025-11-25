"""旅游搭子请求管理器"""

from ..base import TypedPRManager, BasePRManager
from ....schemas.partner_request.travel import TravelPartnerRequest, TravelPRContent


class TravelPRManager(
    TypedPRManager[TravelPRContent, TravelPartnerRequest],
    scheme_cls=TravelPRContent,
    typed_cls=TravelPartnerRequest,
):
    __content_cls__ = TravelPartnerRequest
    __path_prefix__ = BasePRManager.__path_prefix__ + "/travel"
