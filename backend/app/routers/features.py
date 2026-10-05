"""Feature wishes ('Wünsche') with votes and notes."""

from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..models import Feature, FeatureNote, FeatureVote, User
from ..serialize import iso
from ..session import current_user, is_admin, require_admin, require_owner_or_admin, require_user

router = APIRouter(prefix="/api", tags=["features"])


class WunschText(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class WunschErledigen(BaseModel):
    done: bool


class WunschAnmerken(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


def _payload(db: DBSession, features: list[Feature], user: User | None) -> list[dict]:
    if not features:
        return []
    ids = [f.id for f in features]
    votes = defaultdict(set)
    for v in db.exec(select(FeatureVote).where(col(FeatureVote.feature_id).in_(ids))).all():
        votes[v.feature_id].add(v.user_id)
    notes = defaultdict(list)
    for n in db.exec(
        select(FeatureNote).where(col(FeatureNote.feature_id).in_(ids)).order_by(FeatureNote.created_at)
    ).all():
        notes[n.feature_id].append({"id": n.id, "user_id": n.user_id, "text": n.text, "created_at": iso(n.created_at)})
    me = user.id if user else None
    return [
        {
            "id": f.id,
            "text": f.text,
            "user_id": f.user_id,
            "done": f.done,
            "created_at": iso(f.created_at),
            "votes": len(votes[f.id]),
            "voted": me in votes[f.id],
            "notes": notes[f.id],
        }
        for f in features
    ]


def _get(db: DBSession, feature_id: int) -> Feature:
    f = db.get(Feature, feature_id)
    if f is None:
        raise HTTPException(404, "Wunsch nicht gefunden.")
    return f


@router.get("/features")
def list_features(db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    items = _payload(db, list(db.exec(select(Feature).order_by(col(Feature.created_at).desc())).all()), user)
    items.sort(key=lambda x: (x["done"], -x["votes"]))
    return {"features": items}


@router.post("/features", status_code=201)
def add_feature(body: WunschText, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    f = Feature(text=body.text.strip(), user_id=user.id)
    db.add(f)
    db.commit()
    db.refresh(f)
    return _payload(db, [f], user)[0]


@router.patch("/features/{feature_id}")
def edit_feature(
    feature_id: int,
    body: WunschText,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    f = _get(db, feature_id)
    require_owner_or_admin(f.user_id, user, admin)
    f.text = body.text.strip()
    db.add(f)
    db.commit()
    return _payload(db, [f], user)[0]


@router.delete("/features/{feature_id}")
def delete_feature(
    feature_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    f = _get(db, feature_id)
    require_owner_or_admin(f.user_id, user, admin)
    db.delete(f)
    db.commit()
    return {"ok": True}


@router.patch("/features/{feature_id}/done", dependencies=[Depends(require_admin)])
def mark_done(
    feature_id: int,
    body: WunschErledigen,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
):
    f = _get(db, feature_id)
    f.done = body.done
    db.add(f)
    db.commit()
    return _payload(db, [f], user)[0]


@router.post("/features/{feature_id}/vote")
def vote(feature_id: int, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    f = _get(db, feature_id)
    existing = db.exec(
        select(FeatureVote).where(FeatureVote.feature_id == feature_id, FeatureVote.user_id == user.id)
    ).first()
    if existing:
        db.delete(existing)
    else:
        db.add(FeatureVote(feature_id=feature_id, user_id=user.id))
    db.commit()
    return _payload(db, [f], user)[0]


@router.post("/features/{feature_id}/notes", status_code=201)
def add_note(
    feature_id: int, body: WunschAnmerken, user: User = Depends(require_user), db: DBSession = Depends(get_session)
):
    f = _get(db, feature_id)
    db.add(FeatureNote(feature_id=feature_id, user_id=user.id, text=body.text.strip()))
    db.commit()
    return _payload(db, [f], user)[0]


@router.delete("/feature-notes/{note_id}")
def delete_note(
    note_id: int,
    db: DBSession = Depends(get_session),
    user: User | None = Depends(current_user),
    admin: bool = Depends(is_admin),
):
    n = db.get(FeatureNote, note_id)
    if n is None:
        raise HTTPException(404)
    require_owner_or_admin(n.user_id, user, admin)
    db.delete(n)
    db.commit()
    return {"ok": True}
