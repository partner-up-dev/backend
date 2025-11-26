"""Main App Routes."""

import fastapi
from typing import Annotated as Anno, Optional as Opt
from fastapi import Depends, HTTPException, Request, status

from core.auth import AuthInfo, require_auth, get_current_user
from core.engine import get_db_session
import sqlmodel

from .schemas.partner_request import (
    PartnerRequest,
    PartnerRequestRef,
    PartnerRequestEditable,
    PartnerRequestStatus,
    PartnerRequestListType,
    PartnerRequestL2Type,
)

router = fastapi.APIRouter()


@router.get("/partner_request/{pr_id}")
def get_partner_request(
    pr_id: PartnerRequestRef,
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequest:
    """Get a partner request by ID."""
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")
    return pr


@router.get("/partner_request/list/{list_type}")
def get_partner_request_list(
    list_type: PartnerRequestListType,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> list[PartnerRequestRef]:
    """Get a list of partner requests."""
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


@router.put("/partner_request/{pr_id}/publish")
def publish_partner_request(
    pr_id: PartnerRequestRef,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequest:
    """Publish a partner request."""
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")

    if not pr.is_admin(auth.user_id):
        raise HTTPException(status_code=403, detail="Must be admin")

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
    """Cancel a partner request."""
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")

    if not pr.is_admin(auth.user_id):
        raise HTTPException(status_code=403, detail="Must be admin")

    if pr.status not in [PartnerRequestStatus.JOINABLE.value, PartnerRequestStatus.READY.value]:
        raise HTTPException(status_code=409, detail="Cannot cancel")

    pr.status = PartnerRequestStatus.CANCELLED.value
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.put("/partner_request/{pr_id}/status/next")
def next_status(
    pr_id: PartnerRequestRef,
    auth: AuthInfo = Depends(require_auth),
    db: sqlmodel.Session = Depends(get_db_session),
) -> PartnerRequest:
    """Move to next status."""
    pr = db.get(PartnerRequest, pr_id)
    if not pr:
        raise HTTPException(status_code=404, detail="Partner request not found")

    if not pr.is_admin(auth.user_id):
        raise HTTPException(status_code=403, detail="Must be admin")

    current_status = PartnerRequestStatus(pr.status)
    try:
        next_status = current_status.next()
        pr.status = next_status.value
        db.add(pr)
        db.commit()
        db.refresh(pr)
        return pr
    except ValueError:
        raise HTTPException(status_code=409, detail="No next status available")
