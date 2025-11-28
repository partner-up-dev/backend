"""My List Manager."""

import json
import structlog
from fastapi import HTTPException
import sqlmodel

from ..schemas.account import AccountRef
from ..schemas.my_list import MyLists


logger = structlog.get_logger(__name__)


def get_my_lists(db: sqlmodel.Session, account_id: AccountRef) -> MyLists:
    """Get user's lists."""
    lists = db.get(MyLists, account_id)
    if not lists:
        raise HTTPException(status_code=404, detail="Lists not found")
    return lists


def add_to_favorited_prs(
    db: sqlmodel.Session, account_id: AccountRef, pr_id: int
) -> MyLists:
    """Add partner request to favorites."""
    lists = db.get(MyLists, account_id)
    if not lists:
        lists = MyLists(id=account_id, favorited_prs="[]")
        db.add(lists)

    favorited = json.loads(lists.favorited_prs) if lists.favorited_prs else []
    if pr_id not in favorited:
        favorited.append(pr_id)
        lists.favorited_prs = json.dumps(favorited)
        db.add(lists)
        db.commit()
        db.refresh(lists)

    return lists


def remove_from_favorited_prs(
    db: sqlmodel.Session, account_id: AccountRef, pr_id: int
) -> MyLists:
    """Remove partner request from favorites."""
    lists = db.get(MyLists, account_id)
    if not lists:
        raise HTTPException(status_code=404, detail="Lists not found")

    favorited = json.loads(lists.favorited_prs) if lists.favorited_prs else []
    if pr_id in favorited:
        favorited.remove(pr_id)
        lists.favorited_prs = json.dumps(favorited)
        db.add(lists)
        db.commit()
        db.refresh(lists)

    return lists
