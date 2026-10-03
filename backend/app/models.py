"""SQLModel tables for screenmates.

The schema mirrors the reverse-engineered Filmabend app: a movie catalogue
synced from TMDB plus the social layer on top (users, watched log, wishlist,
suggestions, feature requests, host mode).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(timezone.utc)


class Movie(SQLModel, table=True):
    """A film or series. `id` is the TMDB id (negative for seed/local items)."""

    id: int = Field(primary_key=True)
    media_type: str = Field(default="movie", index=True)  # movie | tv
    title: str
    original_title: str = ""
    overview: str = ""
    release_date: str = ""  # YYYY-MM-DD
    year: int | None = Field(default=None, index=True)
    runtime: int | None = None
    poster_path: str = ""
    backdrop_path: str = ""
    vote_average: float = 0.0
    vote_count: int = 0
    popularity: float = 0.0
    genres: str = "[]"  # JSON array of names
    collection: str = ""  # TMDB belongs_to_collection name
    is_canon: bool = Field(default=False, index=True)
    added_at: datetime = Field(default_factory=now)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    color: str = ""
    schutz_movie_id: int | None = None  # "film as PIN" protection
    created_at: datetime = Field(default_factory=now)


class Session(SQLModel, table=True):
    sid: str = Field(primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=now)


class Watched(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True)
    watched_at: datetime = Field(default_factory=now)
    hidden: bool = False
    created_at: datetime = Field(default_factory=now)


class WatchedRating(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True)
    user_id: int = Field(foreign_key="user.id")
    stars: int = 0


class WatchedNote(SQLModel, table=True):
    """Guestbook comment on a watched entry; threaded via parent_id."""

    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    text: str = ""
    parent_id: int | None = None
    created_at: datetime = Field(default_factory=now)


class NoteHeart(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    note_id: int = Field(foreign_key="watchednote.id", index=True)
    user_id: int = Field(foreign_key="user.id")


class WatchedParticipant(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)


class Wishlist(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=now)


class Suggestion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=now)


class Feature(SQLModel, table=True):
    """A feature wish ("Wunsch")."""

    id: int | None = Field(default=None, primary_key=True)
    text: str
    user_id: int | None = Field(default=None, foreign_key="user.id")
    done: bool = False
    created_at: datetime = Field(default_factory=now)


class FeatureVote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    feature_id: int = Field(foreign_key="feature.id", index=True)
    user_id: int = Field(foreign_key="user.id")


class FeatureNote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    feature_id: int = Field(foreign_key="feature.id", index=True)
    user_id: int | None = Field(default=None, foreign_key="user.id")
    text: str = ""
    created_at: datetime = Field(default_factory=now)


class HostState(SQLModel, table=True):
    """Singleton (id=1): host-mode toggle, key combo, and the password film."""

    id: int | None = Field(default=1, primary_key=True)
    an: bool = False
    schluessel: str = ""
    movie_id: int | None = None


class Info(SQLModel, table=True):
    """Singleton (id=1) markdown info panel."""

    id: int | None = Field(default=1, primary_key=True)
    text: str = ""
    updated_at: datetime = Field(default_factory=now)
