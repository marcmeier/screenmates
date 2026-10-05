"""SQLModel tables for screenmates.

A movie catalogue synced from TMDB plus the social layer on top (users,
watched log, wishlist, suggestions, feature wishes, admins, access question).

Children reference their parents with ON DELETE CASCADE, so deleting a user,
a watched entry or a feature never leaves orphans behind. Authorship links
(who wrote a note, who filed a wish) use SET NULL instead: the content stays
when its author is removed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

# Predictable constraint names, so later migrations can address them (SQLite
# batch mode needs names to drop or alter a constraint).
SQLModel.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


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
    keywords: str = ""  # JSON array of TMDB keywords; "" = not fetched yet
    is_canon: bool = Field(default=False, index=True)
    added_at: datetime = Field(default_factory=now)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    color: str = ""
    schutz_movie_id: int | None = None  # "film as PIN" — never sent to clients
    is_admin: bool = False
    freigegeben: bool = True  # False: a name request waiting for an admin
    antrag_gruppe_id: int | None = Field(default=None, foreign_key="gruppe.id", ondelete="SET NULL")  # requested via
    bild: str = ""  # token of the profile picture file, "" = none (see bilder.py)
    vitrine: str = "[]"  # JSON: up to three achievement keys for the profile showcase
    created_at: datetime = Field(default_factory=now)


class Session(SQLModel, table=True):
    sid: str = Field(primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    zugang: bool = False  # came in with an invitation (or had a name)
    einladung_id: int | None = Field(default=None, foreign_key="einladung.id", ondelete="SET NULL")  # with which
    gruppe_id: int | None = Field(default=None, foreign_key="gruppe.id", ondelete="SET NULL")  # active group
    created_at: datetime = Field(default_factory=now)


class Gruppe(SQLModel, table=True):
    """A circle of friends with its own movie nights (see gruppen.py)."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    created_at: datetime = Field(default_factory=now)


class Mitglied(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("gruppe_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    ist_admin: bool = False  # group admin
    dabei: bool = False  # in for this group's next movie night
    seit: datetime = Field(default_factory=now)


class Watched(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
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
    __table_args__ = (UniqueConstraint("gruppe_id", "movie_id"),)

    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    movie_id: int = Field(foreign_key="movie.id", ondelete="CASCADE")
    user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    created_at: datetime = Field(default_factory=now)


class Suggestion(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("gruppe_id", "movie_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    movie_id: int = Field(foreign_key="movie.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=now)


class Abo(SQLModel, table=True):
    """A streaming service someone in the group subscribes to (TMDB provider id)."""

    __table_args__ = (UniqueConstraint("user_id", "provider_id"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    provider_id: int


class Veto(SQLModel, table=True):
    """'Not with me': one veto per person against a currently suggested film.

    The wheel skips vetoed films. A new veto replaces the old one; vetoes go
    when the film is watched or the suggestions are cleared.
    """

    __table_args__ = (UniqueConstraint("gruppe_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    movie_id: int = Field(foreign_key="movie.id", index=True, ondelete="CASCADE")
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


class Einladung(SQLModel, table=True):
    """An invitation link into a group (see routers/einladungen.py)."""

    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    erstellt_von: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    erstellt_am: datetime = Field(default_factory=now)
    gueltig_bis: datetime | None = None
    max_nutzungen: int | None = None  # None: unlimited
    nutzungen: int = 0
    direkt: bool = False  # True: in right away; False: an admin of the group decides
    widerrufen: bool = False
    notiz: str = ""


class Beitrittsanfrage(SQLModel, table=True):
    """Someone with a name asks to join another group (via a link that needs approval)."""

    __table_args__ = (UniqueConstraint("gruppe_id", "user_id"),)

    id: int | None = Field(default=None, primary_key=True)
    gruppe_id: int = Field(foreign_key="gruppe.id", index=True, ondelete="CASCADE")
    user_id: int = Field(foreign_key="user.id", ondelete="CASCADE")
    einladung_id: int | None = Field(default=None, foreign_key="einladung.id", ondelete="SET NULL")
    am: datetime = Field(default_factory=now)


class AppMeta(SQLModel, table=True):
    """Singleton (id=1) for bookkeeping such as the last TMDB sync."""

    id: int | None = Field(default=1, primary_key=True)
    last_sync: datetime | None = None
    erfolge_seit: datetime | None = None  # achievements: data from before this counts as it is
    erfolge_geprueft: bool = False  # the first check ran (its unlocks are marked retroactive)


class KinoState(SQLModel, table=True):
    """One row per group (id = group id) for the live "Kino": what's on air and the secrets for MediaMTX.

    `secret` authenticates the backend's own WHIP/WHEP requests to MediaMTX;
    `obs_key` is the stream key an admin pastes into OBS. Both never leave the
    server except the OBS key, which only admins can see.
    """

    id: int | None = Field(default=1, primary_key=True)
    secret: str = ""
    obs_key: str = ""
    titel: str = ""
    movie_id: int | None = None
    gestartet: datetime | None = None


class Abend(SQLModel, table=True):
    """A group's next movie night date (id = group id). Shown on invitations."""

    id: int | None = Field(default=1, primary_key=True)
    termin: datetime | None = None
    notiz: str = ""  # where, e.g. "bei Marc" or "online im Kino"
    gesetzt_von: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    gesetzt_am: datetime | None = None


class Info(SQLModel, table=True):
    """A group's markdown info panel (id = group id)."""

    id: int | None = Field(default=1, primary_key=True)
    text: str = ""
    updated_at: datetime = Field(default_factory=now)


class Erfolg(SQLModel, table=True):
    """An unlocked achievement (see erfolge.py). Permanent; admins can withdraw it."""

    __table_args__ = (UniqueConstraint("user_id", "schluessel"),)

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    schluessel: str
    am: datetime = Field(default_factory=now)
    gesehen: bool = False  # the unlock pop-up has been shown
    rueckwirkend: bool = False  # unlocked by the first check, for what happened before
    entzogen: bool = False


class Ereignis(SQLModel, table=True):
    """Things achievements need that can't be read from the data afterwards."""

    id: int | None = Field(default=None, primary_key=True)
    typ: str = Field(index=True)  # termin | kino_gesendet | kino_geschaut | treffer
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True, ondelete="CASCADE")
    bezug: str = ""  # termin: date; kino: show start; treffer: watched id
    am: datetime = Field(default_factory=now)
