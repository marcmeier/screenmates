"""Turn ORM rows into the JSON shapes the Vue frontend consumes."""
from __future__ import annotations

import json
from typing import Any

from .config import settings
from .models import Movie, User


def movie_dict(m: Movie, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    base = settings.tmdb_image_base
    d = {
        "id": m.id,
        "media_type": m.media_type,
        "title": m.title,
        "original_title": m.original_title,
        "overview": m.overview,
        "release_date": m.release_date,
        "year": m.year,
        "runtime": m.runtime,
        "poster_path": m.poster_path,
        "backdrop_path": m.backdrop_path,
        "poster_url": f"{base}/w500{m.poster_path}" if m.poster_path else None,
        "backdrop_url": f"{base}/w1280{m.backdrop_path}" if m.backdrop_path else None,
        "vote_average": round(m.vote_average, 1),
        "vote_count": m.vote_count,
        "genres": json.loads(m.genres or "[]"),
        "collection": m.collection,
        "is_canon": m.is_canon,
    }
    if extra:
        d.update(extra)
    return d


def user_dict(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "name": u.name,
        "color": u.color,
        "hat_schutz": u.schutz_movie_id is not None,
    }
