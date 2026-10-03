"""Movies, search, discover, people, credits, similar — the catalogue side.

Every endpoint prefers TMDB and falls back to the local catalogue when no key
is configured, so the app stays usable on seed data.
"""

from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DBSession
from sqlmodel import col, or_, select

from .. import tmdb
from ..config import settings
from ..db import get_session
from ..models import Abo, Movie
from ..serialize import movie_dict, with_flags
from ..util import upsert_movie

router = APIRouter(prefix="/api", tags=["catalog"])

Limit = Annotated[int, Query(ge=1, le=100)]
Page = Annotated[int, Query(ge=1, le=50)]

SORTS = {
    "popularity.desc": (Movie.popularity, True),
    "vote_average.desc": (Movie.vote_average, True),
    "primary_release_date.desc": (Movie.release_date, True),
    "primary_release_date.asc": (Movie.release_date, False),
}


def _ids(csv: str) -> list[int]:
    return [int(x) for x in csv.split(",") if x.strip().isdigit()]


def _profile(path: str | None) -> str | None:
    return f"{settings.tmdb_image_base}/w185{path}" if path else None


@router.get("/movies")
def list_movies(db: DBSession = Depends(get_session), limit: Limit = 60, offset: int = Query(0, ge=0)):
    rows = db.exec(select(Movie).order_by(col(Movie.popularity).desc()).offset(offset).limit(limit)).all()
    return with_flags(db, [movie_dict(m) for m in rows])


@router.get("/movies/{movie_id}")
async def movie_detail(movie_id: int, db: DBSession = Depends(get_session)):
    m = db.get(Movie, movie_id)
    # Rows that came from a list endpoint lack runtime & collection: complete them once.
    if m is None or m.runtime is None:
        data = await tmdb.details(movie_id)
        if data is not None:
            m = upsert_movie(db, data)
            db.commit()
            db.refresh(m)
    if m is None:
        raise HTTPException(404, "Film nicht gefunden.")
    return with_flags(db, [movie_dict(m)])[0]


@router.get("/search/{movie_id}")
async def search_detail(movie_id: int, db: DBSession = Depends(get_session)):
    return await movie_detail(movie_id, db)


@router.get("/movies/{movie_id}/credits")
async def movie_credits(movie_id: int):
    data = await tmdb.credits(movie_id) or {}
    cast = [
        {"id": c["id"], "name": c["name"], "rolle": c.get("character") or "", "bild": _profile(c.get("profile_path"))}
        for c in data.get("cast", [])[:12]
    ]
    crew = [
        {"id": c["id"], "name": c["name"], "rolle": c.get("job") or "", "bild": _profile(c.get("profile_path"))}
        for c in data.get("crew", [])
        if c.get("job") in ("Director", "Screenplay", "Writer", "Original Music Composer")
    ]
    return {"cast": cast, "crew": crew}


@router.get("/movies/{movie_id}/aehnliche")
async def movie_similar(movie_id: int, db: DBSession = Depends(get_session), limit: Limit = 18):
    remote = await tmdb.similar(movie_id)
    if remote is not None:
        return {"results": with_flags(db, [movie_dict(r) for r in remote[:limit]])}
    # Fallback: rank local films by shared genres.
    base = db.get(Movie, movie_id)
    if base is None:
        return {"results": []}
    genres = set(json.loads(base.genres))
    scored = [
        (len(genres & set(json.loads(m.genres))), m) for m in db.exec(select(Movie).where(Movie.id != movie_id)).all()
    ]
    scored.sort(key=lambda t: (t[0], t[1].vote_average), reverse=True)
    return {"results": with_flags(db, [movie_dict(m) for s, m in scored[:limit] if s])}


@router.get("/search")
async def search(
    q: str = Query("", max_length=100), limit: Limit = 24, seite: Page = 1, db: DBSession = Depends(get_session)
):
    q = q.strip()
    if not q:
        return {"results": []}
    remote = await tmdb.search(q, page=seite)
    if remote is not None:
        return {"results": with_flags(db, [movie_dict(r) for r in remote[:limit]])}
    pattern = f"%{q}%"
    rows = db.exec(
        select(Movie)
        .where(or_(col(Movie.title).ilike(pattern), col(Movie.original_title).ilike(pattern)))
        .order_by(col(Movie.popularity).desc())
        .offset((seite - 1) * limit)
        .limit(limit)
    ).all()
    return {"results": with_flags(db, [movie_dict(m) for m in rows])}


@router.get("/discover")
async def discover(
    db: DBSession = Depends(get_session),
    limit: Limit = 24,
    seite: Page = 1,
    sort: str = Query("popularity.desc", pattern="^(" + "|".join(SORTS).replace(".", r"\.") + ")$"),
    include: str = Query("", description="Kommagetrennte TMDB-Genre-IDs, die zusätzlich zu Horror gelten müssen"),
    exclude: str = Query("", description="Kommagetrennte TMDB-Genre-IDs, die ausgeschlossen werden"),
    stimmen_min: int | None = Query(None, ge=0),
    stimmen_max: int | None = Query(None, ge=0),
    dauer_min: int | None = Query(None, ge=0),
    dauer_max: int | None = Query(None, ge=0),
    jahr_min: int | None = Query(None, ge=1880, le=2100),
    jahr_max: int | None = Query(None, ge=1880, le=2100),
    note_min: float | None = Query(None, ge=0, le=10),
    note_max: float | None = Query(None, ge=0, le=10),
    abos: bool = Query(False, description="Nur Filme, die bei einem Abo aus der Gruppe laufen"),
):
    if dauer_min is None:
        dauer_min = tmdb.MIN_RUNTIME
    if sort == "vote_average.desc" and stimmen_min is None:
        stimmen_min = tmdb.MIN_VOTES_FOR_RATING
    flt = dict(
        stimmen_min=stimmen_min,
        stimmen_max=stimmen_max,
        dauer_min=dauer_min,
        dauer_max=dauer_max,
        jahr_min=jahr_min,
        jahr_max=jahr_max,
        note_min=note_min,
        note_max=note_max,
    )
    inc, exc = _ids(include), _ids(exclude)
    anbieter = None
    if abos:
        if not settings.tmdb_enabled:
            return {"results": [], "hinweis": "„Läuft bei uns“ braucht TMDB (TMDB_API_KEY)."}
        anbieter = tmdb.abo_ids(list(set(db.exec(select(Abo.provider_id)).all())))
        if not anbieter:
            return {"results": [], "hinweis": "Noch niemand hat seine Abos eingetragen (Einstellungen)."}
    remote = await tmdb.discover(sort=sort, page=seite, include=inc, exclude=exc, abo_anbieter=anbieter, **flt)
    if remote is not None:
        return {"results": with_flags(db, [movie_dict(r) for r in remote[:limit]])}

    stmt = select(Movie)
    for column, lo, hi in (
        (Movie.vote_count, stimmen_min, stimmen_max),
        (Movie.runtime, dauer_min, dauer_max),
        (Movie.year, jahr_min, jahr_max),
        (Movie.vote_average, note_min, note_max),
    ):
        # Rows synced from list results have no runtime yet; don't hide them for it.
        if lo is not None:
            stmt = stmt.where(or_(col(column).is_(None), column >= lo))
        if hi is not None:
            stmt = stmt.where(or_(col(column).is_(None), column <= hi))
    sort_col, desc = SORTS[sort]
    stmt = stmt.order_by(col(sort_col).desc() if desc else col(sort_col).asc())
    inc_names = {tmdb.GENRES[g] for g in inc if g in tmdb.GENRES}
    exc_names = {tmdb.GENRES[g] for g in exc if g in tmdb.GENRES}
    rows = [
        m
        for m in db.exec(stmt).all()
        if inc_names <= set(json.loads(m.genres)) and not exc_names & set(json.loads(m.genres))
    ]
    page = rows[(seite - 1) * limit : seite * limit]
    return {"results": with_flags(db, [movie_dict(m) for m in page])}


@router.get("/movies/{movie_id}/anbieter")
async def where_to_watch(movie_id: int, db: DBSession = Depends(get_session)):
    """Where the film streams in the region, and who in the group has that subscription."""
    data = await tmdb.watch_providers(movie_id)
    if data is None:
        return {"verfuegbar": False}
    wer: dict[int, list[int]] = {}
    for uid, pid in db.exec(select(Abo.user_id, Abo.provider_id)).all():
        wer.setdefault(pid, []).append(uid)
    main = lambda pid: tmdb.ABO_VARIANTE.get(pid, pid)  # noqa: E731
    abo = [p | {"bei": sorted(wer.get(main(p["id"]), []))} for p in data["abo"]]
    abo.sort(key=lambda p: not p["bei"])  # what we already pay for comes first
    return {"verfuegbar": True, "quelle": "JustWatch", "region": settings.tmdb_region, **data, "abo": abo}


@router.get("/movies/{movie_id}/trailer")
async def movie_trailer(movie_id: int):
    """`trailer` is null when there is none: a normal case, not an error."""
    return {"trailer": await tmdb.trailer(movie_id)}


@router.get("/anbieter")
async def providers(limit: Limit = 40, db: DBSession = Depends(get_session)):
    """Streaming services to pick from, plus every one someone already has."""
    alle = await tmdb.provider_list()
    if alle is None:
        return {"anbieter": [], "verfuegbar": False}
    gewaehlt = set(db.exec(select(Abo.provider_id)).all())
    # only real subscriptions: no rent/buy shops, no "with ads" duplicates
    abos = [p for p in alle if p["id"] not in tmdb.STORE_IDS and p["id"] not in tmdb.ABO_VARIANTE]
    auswahl = [p for i, p in enumerate(abos) if i < limit or p["id"] in gewaehlt]
    return {"anbieter": auswahl, "verfuegbar": True}


@router.get("/genres")
def genres():
    return {"genres": [{"id": k, "name": v} for k, v in sorted(tmdb.GENRES.items(), key=lambda kv: kv[1])]}


DEPARTMENTS = {
    "Acting": "Schauspiel",
    "Directing": "Regie",
    "Writing": "Drehbuch",
    "Production": "Produktion",
    "Sound": "Musik",
    "Camera": "Kamera",
    "Editing": "Schnitt",
    "Visual Effects": "Effekte",
    "Art": "Szenenbild",
    "Costume & Make-Up": "Kostüm & Maske",
    "Lighting": "Licht",
    "Crew": "Crew",
}


@router.get("/personen")
async def people(q: str = Query("", max_length=100)):
    if not q.strip():
        return {"results": []}
    results = await tmdb.person_search(q.strip()) or []
    people = [
        {
            "id": p["id"],
            "name": p["name"],
            "bereich": DEPARTMENTS.get(p.get("known_for_department") or "", p.get("known_for_department") or ""),
            "bild": _profile(p.get("profile_path")),
            "bekannt_fuer": [k.get("title") or k.get("name") for k in p.get("known_for", [])][:3],
            "horror": any(tmdb.HORROR in k.get("genre_ids", []) for k in p.get("known_for", [])),
        }
        for p in results
    ]
    # This is a horror app: "carpenter" should find John before Sabrina.
    # Stable sort keeps TMDB's popularity order within each group.
    people.sort(key=lambda p: not p["horror"])
    return {"results": people}


JOBS = {
    "Director": "Regie",
    "Screenplay": "Drehbuch",
    "Writer": "Drehbuch",
    "Story": "Story",
    "Novel": "Romanvorlage",
    "Characters": "Figuren",
    "Producer": "Produktion",
    "Executive Producer": "Ausführende Produktion",
    "Original Music Composer": "Musik",
    "Music": "Musik",
    "Director of Photography": "Kamera",
    "Editor": "Schnitt",
}


def _is_cameo(rolle: str) -> bool:
    """Documentary appearances and thank-you credits aren't part of someone's work."""
    r = rolle.lower()
    return r in ("self", "himself", "herself", "thanks") or "archive footage" in r or r.startswith("self ")


@router.get("/personen/{person_id}/filme")
async def person_films(person_id: int, nur_horror: bool = True, db: DBSession = Depends(get_session)):
    info, data = await asyncio.gather(tmdb.person(person_id), tmdb.person_movies(person_id))
    if data is None:
        raise HTTPException(404, "Person nicht gefunden.")
    seen: dict[int, dict] = {}
    # Crew first, so "Regie" leads and an uncredited cameo comes last.
    for credit in [*data.get("crew", []), *data.get("cast", [])]:
        if nur_horror and tmdb.HORROR not in credit.get("genre_ids", []):
            continue
        rolle = credit.get("character") or JOBS.get(credit.get("job") or "", credit.get("job") or "")
        if _is_cameo(rolle):
            continue
        if credit["id"] in seen:
            if rolle and rolle not in seen[credit["id"]]["rollen"]:
                seen[credit["id"]]["rollen"].append(rolle)
            continue
        seen[credit["id"]] = movie_dict(tmdb.normalise(credit)) | {"rollen": [rolle] if rolle else []}
    # Best-known first: a filmography should open with Halloween, not a 2026 making-of.
    films = sorted(seen.values(), key=lambda m: m["vote_count"], reverse=True)
    return {"person": {"id": person_id, "name": (info or {}).get("name", "")}, "results": with_flags(db, films)}
