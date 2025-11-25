import typing
from typing import Optional as Opt, Annotated as Anno
from .travel import TravelPRManager
from .trip.commute import CommutePRManager
from .trip.ride_hailing import RideHailingPRManager
from ...schemas.partner_request import PartnerRequestL2Type

if typing.TYPE_CHECKING:
    from .base import TypedPRManager

PRManagerMapper: typing.Dict[PartnerRequestL2Type, type["TypedPRManager"]] = {
    PartnerRequestL2Type.RIDE_HAILING: RideHailingPRManager,
    PartnerRequestL2Type.COMMUTE: CommutePRManager,
    PartnerRequestL2Type.HITCHHIKING: None,  # TODO
    PartnerRequestL2Type.MOPED: None,  # TODO
    PartnerRequestL2Type.TRAVEL: TravelPRManager,
}
