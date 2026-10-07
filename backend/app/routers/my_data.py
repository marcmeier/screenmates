"""Your own data: download everything screenmates keeps about you, or delete your name.

The export is one JSON file with what is yours (profile, groups, ratings, comments,
suggestions, wishes, awards, chat messages, notifications, devices, AI searches).
Deleting your name removes everything that is yours alone; comments in a guestbook
and chat messages stay, without your name, like when an admin deletes a name. The
last admin can't leave: there must always be one.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session as DBSession
from sqlmodel import col, func, select

from .. import bilder, erfolge, push
from ..db import get_session
from ..models import (
    Abo,
    Benachrichtigung,
    Feature,
    FeatureNote,
    FeatureVote,
    Gruppe,
    KiAnfrage,
    KinoNachricht,
    Mitglied,
    Movie,
    NoteHeart,
    PushAbo,
    SessionName,
    Suggestion,
    TerminStimme,
    TerminVorschlag,
    User,
    Veto,
    Watched,
    WatchedNote,
    WatchedParticipant,
    WatchedRating,
    Wishlist,
)
from ..serialize import iso
from ..session import require_user
from ..version import __version__
from .users import ensure_not_last_admin

router = APIRouter(prefix="/api/users/me", tags=["users"])


def _titel(db: DBSession, ids: set[int]) -> dict[int, str]:
    return dict(db.exec(select(Movie.id, Movie.title).where(col(Movie.id).in_(ids))).all()) if ids else {}


@router.get("/export")
def export(request: Request, user: User = Depends(require_user), db: DBSession = Depends(get_session)):
    """Everything about you, as a file to keep (GDPR Art. 15 and 20)."""

    uid = user.id
    gruppen = {g.id: g.name for g in db.exec(select(Gruppe)).all()}
    watched = {w.id: w for w in db.exec(select(Watched)).all()}
    bewertungen = db.exec(select(WatchedRating).where(WatchedRating.user_id == uid)).all()
    dabei = db.exec(select(WatchedParticipant).where(WatchedParticipant.user_id == uid)).all()
    notizen = db.exec(select(WatchedNote).where(WatchedNote.user_id == uid)).all()
    vorschlaege = db.exec(select(Suggestion).where(Suggestion.user_id == uid)).all()
    merkliste = db.exec(select(Wishlist).where(Wishlist.user_id == uid)).all()
    vetos = db.exec(select(Veto).where(Veto.user_id == uid)).all()
    filme = _titel(
        db,
        {watched[x.watched_id].movie_id for x in [*bewertungen, *dabei, *notizen] if x.watched_id in watched}
        | {x.movie_id for x in [*vorschlaege, *merkliste, *vetos]},
    )

    def abend(watched_id: int) -> dict:
        w = watched.get(watched_id)
        if w is None:
            return {}
        return {
            "film": filme.get(w.movie_id),
            "movie_id": w.movie_id,
            "group": gruppen.get(w.gruppe_id),
            "watched_at": iso(w.watched_at),
        }

    def liste(rows) -> list[dict]:
        return [
            {
                "film": filme.get(r.movie_id),
                "movie_id": r.movie_id,
                "group": gruppen.get(r.gruppe_id),
                "added": iso(r.created_at),
            }
            for r in rows
        ]

    vorschlag_termine = {v.id: v for v in db.exec(select(TerminVorschlag)).all()}
    meine = erfolge.freigeschaltet(db).get(uid, {})
    daten = {
        "exported_at": iso(datetime.now(UTC)),
        "screenmates_version": __version__,
        "profile": {
            "id": uid,
            "name": user.name,
            "color": user.color,
            "created_at": iso(user.created_at),
            "admin": user.is_admin,
            "settings": json.loads(user.design or "{}"),
            "profile_picture": f"{request.base_url}api/users/{uid}/bild?v={user.bild}" if user.bild else None,
            "showcase": json.loads(user.vitrine or "[]"),
            "calendar_feed": bool(user.kalender),
            "notifications": push.wahl(user),
        },
        "groups": [
            {
                "group": gruppen.get(m.gruppe_id),
                "admin": m.ist_admin,
                "member_since": iso(m.seit),
                "next_night": "ja" if m.dabei else m.rueckmeldung or None,
            }
            for m in db.exec(select(Mitglied).where(Mitglied.user_id == uid)).all()
        ],
        "streaming_services": sorted(db.exec(select(Abo.provider_id).where(Abo.user_id == uid)).all()),
        "ratings": [abend(r.watched_id) | {"stars": r.stars} for r in bewertungen],
        "evenings": [abend(p.watched_id) for p in dabei],
        "comments": [
            abend(n.watched_id) | {"text": n.text, "written": iso(n.created_at), "replying": n.parent_id is not None}
            for n in notizen
        ],
        "hearts_given": db.exec(select(func.count()).select_from(NoteHeart).where(NoteHeart.user_id == uid)).one(),
        "suggestions": liste(vorschlaege),
        "watchlist": liste(merkliste),
        "vetoes": liste(vetos),
        "date_poll_answers": [
            {"date": iso(vorschlag_termine[s.vorschlag_id].termin), "answer": s.antwort}
            for s in db.exec(select(TerminStimme).where(TerminStimme.user_id == uid)).all()
            if s.vorschlag_id in vorschlag_termine
        ],
        "wishes": [
            {"text": f.text, "done": f.done, "written": iso(f.created_at)}
            for f in db.exec(select(Feature).where(Feature.user_id == uid)).all()
        ],
        "wish_notes": [
            {"text": n.text, "written": iso(n.created_at)}
            for n in db.exec(select(FeatureNote).where(FeatureNote.user_id == uid)).all()
        ],
        "wish_votes": db.exec(select(func.count()).select_from(FeatureVote).where(FeatureVote.user_id == uid)).one(),
        "awards": [
            {"award": erfolge.NACH_KEY[k].anzeige_name, "key": k, "unlocked": iso(e.am)}
            for k, e in sorted(meine.items())
        ],
        "cinema_chat": [
            {"group": gruppen.get(n.gruppe_id), "text": n.text, "at": iso(n.am)}
            for n in db.exec(select(KinoNachricht).where(KinoNachricht.user_id == uid)).all()
        ],
        "bell": [
            {"title": b.titel, "text": b.text, "at": iso(b.am), "read": b.gelesen}
            for b in db.exec(select(Benachrichtigung).where(Benachrichtigung.user_id == uid)).all()
        ],
        "push_devices": [
            {"device": a.geraet, "since": iso(a.am)}
            for a in db.exec(select(PushAbo).where(PushAbo.user_id == uid)).all()
        ],
        "browsers_with_this_name": db.exec(
            select(func.count()).select_from(SessionName).where(SessionName.user_id == uid)
        ).one(),
        "ai_searches": [
            {
                "at": iso(a.at),
                "model": a.modell,
                "tokens_in": a.tokens_ein,
                "tokens_out": a.tokens_aus,
                "cost_usd": a.kosten,
            }
            for a in db.exec(select(KiAnfrage).where(KiAnfrage.user_id == uid)).all()
        ],
    }
    datei = re.sub(r"[^A-Za-z0-9_-]+", "-", user.name).strip("-") or "name"
    return JSONResponse(daten, headers={"Content-Disposition": f'attachment; filename="screenmates-{datei}.json"'})


@router.delete("")
def delete_me(
    name: str = Query(..., description="Your name, typed again to confirm"),
    user: User = Depends(require_user),
    db: DBSession = Depends(get_session),
):
    """Delete your own name and everything that is yours alone (GDPR Art. 17)."""
    if name.strip() != user.name:
        raise HTTPException(422, "Zum Bestätigen deinen Namen genau so eintippen.")
    ensure_not_last_admin(db, user)
    uid, bild = user.id, user.bild
    db.delete(user)
    db.commit()
    bilder.loeschen(uid, bild)
    return {"ok": True}
