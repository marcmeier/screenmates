"""Movies, search, discover, people, credits, similar — the catalogue side."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import tmdb
from ..db import get_session
from ..models import Movie
from ..serialize import movie_dict

router = APIRouter(prefix="/api", tags=["catalog"])


def _upsert(db: DBSession, raw: dict, media_type: str | None = None, is_canon: bool = False) -> Movie:
    existing = db.get(Movie, raw["id"])
    data = tmdb.normalise(raw, media_type)
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        if is_canon:
            existing.is_canon = True
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    m = Movie(is_canon=is_canon, **data)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/movies")
def list_movies(db: DBSession = Depends(get_session), limit: int = 60):
    rows = db.exec(select(Movie).order_by(Movie.popularity.desc()).limit(limit)).all()
    return [movie_dict(m) for m in rows]


@router.get("/movies/{movie_id}")
async def movie_detail(movie_id: int, db: DBSession = Depends(get_session)):
    m = db.get(Movie, movie_id)
    if m is None:
        det = await tmdb.details(movie_id)
        if det is None:
            raise HTTPException(404, "Film nicht gefunden")
        m = _upsert(db, det)
    return movie_dict(m)


@router.get("/movies/{movie_id}/credits")
async def movie_credits(movie_id: int, db: DBSession = Depends(get_session)):
    m = db.get(Movie, movie_id)
    media = m.media_type if m else "movie"
    return await tmdb.credits(movie_id, media)


@router.get("/movies/{movie_id}/aehnliche")
async def movie_similar(movie_id: int, db: DBSession = Depends(get_session)):
    m = db.get(Movie, movie_id)
    media = m.media_type if m else "movie"
    results = await tmdb.similar(movie_id, media)
    return {"results": results}


@router.get("/search")
async def search(q: str = Query(""), limit: int = 24, db: DBSession = Depends(get_session)):
    q = q.strip()
    if not q:
        return {"results": []}
    remote = await tmdb.search(q, limit)
    if remote:
        return {"results": remote}
    # Fallback: local title search over seed data.
    like = f"%{q.lower()}%"
    rows = db.exec(select(Movie).limit(limit)).all()
    hits = [movie_dict(m) for m in rows if q.lower() in m.title.lower() or q.lower() in m.original_title.lower()]
    return {"results": hits[:limit]}


@router.get("/search/{movie_id}")
async def search_detail(movie_id: int, db: DBSession = Depends(get_session)):
    return await movie_detail(movie_id, db)


@router.get("/discover")
async def discover(
    db: DBSession = Depends(get_session),
    limit: int = 24,
    sort: str = "popularity.desc",
    include: str = "",
    exclude: str = "",
    stimmen_min: int | None = None,
    stimmen_max: int | None = None,
    dauer_min: int | None = None,
    dauer_max: int | None = None,
    jahr_min: int | None = None,
    jahr_max: int | None = None,
    note_min: float | None = None,
    note_max: float | None = None,
):
    flt = dict(
        stimmen_min=stimmen_min, dauer_min=dauer_min, dauer_max=dauer_max,
        jahr_min=jahr_min, jahr_max=jahr_max, note_min=note_min, note_max=note_max,
    )
    remote = await tmdb.discover_horror(limit=limit, sort=sort, **flt)
    if remote:
        return {"results": remote}
    # Fallback to local catalogue filtered in Python.
    rows = db.exec(select(Movie)).all()
    def ok(m: Movie) -> bool:
        if jahr_min and (m.year or 0) < jahr_min:
            return False
        if jahr_max and (m.year or 9999) > jahr_max:
            return False
        if note_min and m.vote_average < note_min:
            return False
        if stimmen_min and m.vote_count < stimmen_min:
            return False
        return True
    rows = sorted([m for m in rows if ok(m)], key=lambda m: m.popularity, reverse=True)
    return {"results": [movie_dict(m) for m in rows[:limit]]}


@router.get("/personen")
async def people(q: str = Query("")):
    if not q.strip():
        return {"results": []}
    return {"results": await tmdb.person_search(q.strip())}


@router.get("/personen/{person_id}/filme")
async def person_films(person_id: int):
    data = await tmdb.person_movies(person_id)
    cast = data.get("cast", [])
    crew = data.get("crew", [])
    return {"cast": cast, "crew": crew}
