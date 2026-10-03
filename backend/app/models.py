"""SQLModel tables for screenmates.

A movie catalogue synced from TMDB plus the social layer on top (users,
watched log, wishlist, suggestions, feature wishes, host mode).

Children reference their parents with ON DELETE CASCADE, so deleting a user,
a watched entry or a feature never leaves orphans behind. Authorship links
(who wrote a note, who filed a wish) use SET NULL instead: the content stays
when its author is removed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now(UTC)


class Movie(SQLModel, table=True):
    """A film. `id` is the TMDB movie id."""

    id: int = Field(primary_key=True)
    media_type: str = Field(default="movie", index=True)
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
    genres: str = "[]"  # JSON array of genre names
    collection: str = ""  # TMDB belongs_to_collection name
    is_canon: bool = Field(default=False, index=True)
    added_at: datetime = Field(default_factory=now)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str = ""
    schutz_movie_id: int | None = None  # "film as PIN" — never sent to clients
    dabei: bool = False  # in for the next movie night
    created_at: datetime = Field(default_factory=now)


class Session(SQLModel, table=True):
    sid: str = Field(primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    is_host: bool = False
    created_at: datetime = Field(default_factory=now)


class Watched(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True, ondelete="CASCADE")
    watched_at: datetime = Field(default_factory=now)
    hidden: bool = False
    created_at: datetime = Field(default_factory=now)


class WatchedRating(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("watched_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    stars: int = 0


class WatchedNote(SQLModel, table=True):
    """Guestbook comment on a watched entry; threaded via parent_id."""

    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True, ondelete="CASCADE")
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    text: str = ""
    parent_id: int | None = Field(default=None, foreign_key="watchednote.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=now)


class NoteHeart(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("note_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    note_id: int = Field(foreign_key="watchednote.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")


class WatchedParticipant(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("watched_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    watched_id: int = Field(foreign_key="watched.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")


class Wishlist(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", unique=True, ondelete="CASCADE")
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    created_at: datetime = Field(default_factory=now)


class Suggestion(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("movie_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    movie_id: int = Field(foreign_key="movie.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=now)


class Feature(SQLModel, table=True):
    """A feature wish ("Wunsch")."""

    id: int | None = Field(default=None, primary_key=True)
    text: str
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    done: bool = False
    created_at: datetime = Field(default_factory=now)


class FeatureVote(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("feature_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    feature_id: int = Field(foreign_key="feature.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")


class FeatureNote(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    feature_id: int = Field(foreign_key="feature.id", index=True, ondelete="CASCADE")
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    text: str = ""
    created_at: datetime = Field(default_factory=now)


class HostState(SQLModel, table=True):
    """Singleton (id=1) holding the host password film."""

    id: int | None = Field(default=1, primary_key=True)
    movie_id: int | None = None


class AppMeta(SQLModel, table=True):
    """Singleton (id=1) for bookkeeping such as the last TMDB sync."""

    id: int | None = Field(default=1, primary_key=True)
    last_sync: datetime | None = None


class KinoState(SQLModel, table=True):
    """Singleton (id=1) for the live "Kino": what's on air and the secrets for MediaMTX.

    `secret` authenticates the backend's own WHIP/WHEP requests to MediaMTX;
    `obs_key` is the stream key the host pastes into OBS. Both never leave the
    server except the OBS key, which only the host can see.
    """

    id: int | None = Field(default=1, primary_key=True)
    secret: str = ""
    obs_key: str = ""
    titel: str = ""
    movie_id: int | None = None
    gestartet: datetime | None = None


class Info(SQLModel, table=True):
    """Singleton (id=1) markdown info panel."""

    id: int | None = Field(default=1, primary_key=True)
    text: str = ""
    updated_at: datetime = Field(default_factory=now)
