"""Feature wishes ('Wünsche') with votes and notes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session as DBSession
from sqlmodel import select

from ..db import get_session
from ..models import Feature, FeatureNote, FeatureVote, User
from ..session import current_user

router = APIRouter(prefix="/api", tags=["features"])


class WunschAnlegen(BaseModel):
    text: str


class WunschAendern(BaseModel):
    text: str


class WunschErledigen(BaseModel):
    done: bool


class WunschAnmerken(BaseModel):
    text: str


def _dict(db: DBSession, f: Feature, user: User | None) -> dict:
    votes = db.exec(select(FeatureVote).where(FeatureVote.feature_id == f.id)).all()
    notes = db.exec(select(FeatureNote).where(FeatureNote.feature_id == f.id).order_by(FeatureNote.created_at)).all()
    return {
        "id": f.id,
        "text": f.text,
        "user_id": f.user_id,
        "done": f.done,
        "created_at": f.created_at.isoformat(),
        "votes": len(votes),
        "voted": any(v.user_id == (user.id if user else None) for v in votes),
        "notes": [{"id": n.id, "user_id": n.user_id, "text": n.text, "created_at": n.created_at.isoformat()} for n in notes],
    }


@router.get("/features")
def list_features(db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    rows = db.exec(select(Feature).order_by(Feature.done, Feature.created_at.desc())).all()
    items = [_dict(db, f, user) for f in rows]
    items.sort(key=lambda x: (x["done"], -x["votes"]))
    return {"features": items}


@router.post("/features")
def add_feature(body: WunschAnlegen, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    f = Feature(text=body.text, user_id=user.id if user else None)
    db.add(f)
    db.commit()
    db.refresh(f)
    return _dict(db, f, user)


@router.patch("/features/{feature_id}")
def edit_feature(feature_id: int, body: WunschAendern, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    f = db.get(Feature, feature_id)
    if f is None:
        raise HTTPException(404)
    f.text = body.text
    db.add(f)
    db.commit()
    return _dict(db, f, user)


@router.delete("/features/{feature_id}")
def delete_feature(feature_id: int, db: DBSession = Depends(get_session)):
    f = db.get(Feature, feature_id)
    if f:
        db.delete(f)
        db.commit()
    return {"ok": True}


@router.patch("/features/{feature_id}/done")
def mark_done(feature_id: int, body: WunschErledigen, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    f = db.get(Feature, feature_id)
    if f is None:
        raise HTTPException(404)
    f.done = body.done
    db.add(f)
    db.commit()
    return _dict(db, f, user)


@router.post("/features/{feature_id}/vote")
def vote(feature_id: int, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    if user is None:
        raise HTTPException(401)
    existing = db.exec(
        select(FeatureVote).where(FeatureVote.feature_id == feature_id, FeatureVote.user_id == user.id)
    ).first()
    if existing:
        db.delete(existing)
    else:
        db.add(FeatureVote(feature_id=feature_id, user_id=user.id))
    db.commit()
    return _dict(db, db.get(Feature, feature_id), user)


@router.post("/features/{feature_id}/notes")
def add_note(feature_id: int, body: WunschAnmerken, db: DBSession = Depends(get_session), user: User | None = Depends(current_user)):
    n = FeatureNote(feature_id=feature_id, user_id=user.id if user else None, text=body.text)
    db.add(n)
    db.commit()
    return _dict(db, db.get(Feature, feature_id), user)


@router.delete("/feature-notes/{note_id}")
def delete_note(note_id: int, db: DBSession = Depends(get_session)):
    n = db.get(FeatureNote, note_id)
    if n:
        db.delete(n)
        db.commit()
    return {"ok": True}
