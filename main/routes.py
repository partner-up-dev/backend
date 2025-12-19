"""Main App Routes.

Business logic endpoints for partner requests.
Simple CRUD operations (get, create, put, delete, upsert) are handled by direct
database access from the client.
"""

import fastapi
from fastapi import Depends, HTTPException

from core.auth import AuthInfo, require_auth
from core.engine import get_db_session
import sqlmodel

from .schemas.partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestStatus,
    PartnerRequestListType,
    PartnerRequestL2Type,
)
from .schemas.partner_request.trip.create import RideHailingPRCreate, CommutePRCreate
from .managers.partner_request.trip.ride_hailing import RideHailingPRManager
from .managers.partner_request.trip.commute import CommutePRManager

router = fastapi.APIRouter()


@router.get("/partner_request/list/{list_type}")
def get_partner_request_list(
    list_type: PartnerRequestListType,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> list[PartnerRequestRef]:
    """Get a list of partner requests.

    Filters partner requests by list type for the authenticated user.
    """
    result: list[PartnerRequestRef] = []
    account_id = auth.user_id

    if list_type == PartnerRequestListType.ONGOING:
        statement = sqlmodel.select(PartnerRequest.id).where(
            PartnerRequest.created_by == account_id,
            PartnerRequest.status.in_([s.value for s in PartnerRequestStatus.ongoing_status()]),
        )
        results = db.exec(statement).all()
        result.extend(results)

    elif list_type == PartnerRequestListType.HISTORY:
        statement = sqlmodel.select(PartnerRequest.id).where(
            PartnerRequest.created_by == account_id,
            PartnerRequest.status.in_([s.value for s in PartnerRequestStatus.closed_status()]),
        )
        results = db.exec(statement).all()
        result.extend(results)

    elif list_type == PartnerRequestListType.DRAFT:
        statement = sqlmodel.select(PartnerRequest.id).where(
            PartnerRequest.created_by == account_id,
            PartnerRequest.status == PartnerRequestStatus.DRAFT.value,
        )
        results = db.exec(statement).all()
        result.extend(results)

    return result


@router.post("/partner_request/{pr_type}")
def create_partner_request(
    pr_type: PartnerRequestL2Type,
    data: RideHailingPRCreate | CommutePRCreate,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequestRef:
    """Create a partner request.

    Creates both base PartnerRequest and type-specific content records.
    The type of partner request is determined by the pr_type path parameter.
    """
    account_id = auth.user_id

    if pr_type == PartnerRequestL2Type.RIDE_HAILING:
        if not isinstance(data, RideHailingPRCreate):
            raise HTTPException(status_code=400, detail="Invalid data for ride_hailing type")
        pr_id = RideHailingPRManager.create(account_id, data, db)
    elif pr_type == PartnerRequestL2Type.COMMUTE:
        if not isinstance(data, CommutePRCreate):
            raise HTTPException(status_code=400, detail="Invalid data for commute type")
        pr_id = CommutePRManager.create(account_id, data, db)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported partner request type: {pr_type}")

    return pr_id


@router.put("/partner_request/{pr_id}/publish")
def publish_partner_request(
    pr_id: PartnerRequestRef,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequest:
    """Publish a partner request.

    Changes status from DRAFT to JOINABLE.
    Only the admin (creator) can publish.
    Idempotent: if already JOINABLE, returns the request without error.
    """
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")

    if not pr.is_admin(auth.user_id):
        raise HTTPException(status_code=403, detail="Must be admin")

    # Idempotent: if already published, just return
    if pr.status == PartnerRequestStatus.JOINABLE.value:
        return pr

    if pr.status != PartnerRequestStatus.DRAFT.value:
        raise HTTPException(status_code=409, detail="Can only publish draft")

    pr.status = PartnerRequestStatus.JOINABLE.value
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.put("/partner_request/{pr_id}/cancel")
def cancel_partner_request(
    pr_id: PartnerRequestRef,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequest:
    """Cancel a partner request.

    Changes status to CANCELLED.
    Only the admin (creator) can cancel.
    Can only cancel if status is JOINABLE or READY.
    Idempotent: if already CANCELLED, returns the request without error.
    """
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")

    if not pr.is_admin(auth.user_id):
        raise HTTPException(status_code=403, detail="Must be admin")

    # Idempotent: if already cancelled, just return
    if pr.status == PartnerRequestStatus.CANCELLED.value:
        return pr

    if pr.status not in [PartnerRequestStatus.JOINABLE.value, PartnerRequestStatus.READY.value]:
        raise HTTPException(status_code=409, detail="Cannot cancel")

    pr.status = PartnerRequestStatus.CANCELLED.value
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr
