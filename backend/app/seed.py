"""Seed catalogue so screenmates is usable before a TMDB key is configured.

Real TMDB ids are used so that, once a key is added and `/api/sync` (or a detail
fetch) runs, these rows upgrade in place with posters and full metadata. Titles
and plots follow TMDB_LANGUAGE like real film data: German, or else English."""

from __future__ import annotations

import json

from sqlmodel import Session, select

from .config import settings
from .db import engine
from .models import Movie

SEED: list[dict] = [
    dict(
        id=694,
        title="Shining",
        original_title="The Shining",
        year=1980,
        runtime=146,
        vote_average=8.2,
        vote_count=18000,
        genres=["Horror", "Thriller"],
        overview="Ein Schriftsteller wird Hausmeister eines abgelegenen Hotels und verliert dort langsam den Verstand.",
        overview_en="A writer takes a job as winter caretaker of a remote hotel and slowly loses his mind.",
    ),
    dict(
        id=9552,
        title="Der Exorzist",
        original_title="The Exorcist",
        year=1973,
        runtime=122,
        vote_average=7.9,
        vote_count=8000,
        genres=["Horror"],
        overview="Eine Mutter sucht Hilfe, als ihre Tochter von einer dämonischen Macht besessen scheint.",
        overview_en="A mother seeks help when her daughter seems possessed by a demonic force.",
    ),
    dict(
        id=348,
        title="Alien",
        original_title="Alien",
        year=1979,
        runtime=117,
        vote_average=8.2,
        vote_count=14000,
        genres=["Horror", "Science Fiction"],
        overview="Die Crew eines Raumfrachters wird von einem tödlichen außerirdischen Organismus gejagt.",
        overview_en="The crew of a space freighter is hunted by a deadly alien organism.",
    ),
    dict(
        id=1091,
        title="Das Ding aus einer anderen Welt",
        original_title="The Thing",
        year=1982,
        runtime=109,
        vote_average=8.2,
        vote_count=9000,
        genres=["Horror", "Science Fiction"],
        overview="In einer Antarktis-Station imitiert ein außerirdisches Wesen seine Opfer.",
        overview_en="At an Antarctic research station, an alien creature imitates its victims.",
    ),
    dict(
        id=948,
        title="Halloween",
        original_title="Halloween",
        year=1978,
        runtime=91,
        vote_average=7.6,
        vote_count=6000,
        genres=["Horror", "Thriller"],
        overview="Der entflohene Mörder Michael Myers kehrt an Halloween in seine Heimatstadt zurück.",
        overview_en="Escaped killer Michael Myers returns to his hometown on Halloween night.",
    ),
    dict(
        id=377,
        title="Nightmare – Mörderische Träume",
        original_title="A Nightmare on Elm Street",
        year=1984,
        runtime=91,
        vote_average=7.4,
        vote_count=5500,
        genres=["Horror"],
        overview="Freddy Krueger tötet Teenager in ihren Träumen.",
        overview_en="Freddy Krueger kills teenagers in their dreams.",
    ),
    dict(
        id=4232,
        title="Scream",
        original_title="Scream",
        year=1996,
        runtime=111,
        vote_average=7.4,
        vote_count=7000,
        genres=["Horror", "Mystery"],
        overview="Ein maskierter Killer terrorisiert eine Kleinstadt und ihre horrorfilmkundigen Teenager.",
        overview_en="A masked killer terrorises a small town and its horror-savvy teenagers.",
    ),
    dict(
        id=346364,
        title="Es",
        original_title="It",
        year=2017,
        runtime=135,
        vote_average=7.3,
        vote_count=18000,
        genres=["Horror"],
        overview="Sieben Kinder stellen sich einem uralten, gestaltwandelnden Grauen.",
        overview_en="Seven kids face an ancient, shape-shifting evil.",
    ),
    dict(
        id=138843,
        title="Conjuring – Die Heimsuchung",
        original_title="The Conjuring",
        year=2013,
        runtime=112,
        vote_average=7.5,
        vote_count=10000,
        genres=["Horror", "Thriller"],
        overview="Zwei Dämonologen helfen einer Familie, die von einer dunklen Präsenz heimgesucht wird.",
        overview_en="Two demonologists help a family haunted by a dark presence.",
    ),
    dict(
        id=419430,
        title="Get Out",
        original_title="Get Out",
        year=2017,
        runtime=104,
        vote_average=7.6,
        vote_count=15000,
        genres=["Horror", "Mystery", "Thriller"],
        overview="Ein Besuch bei den Eltern der Freundin wird zum Albtraum.",
        overview_en="A visit to his girlfriend's parents turns into a nightmare.",
    ),
    dict(
        id=493922,
        title="Hereditary – Das Vermächtnis",
        original_title="Hereditary",
        year=2018,
        runtime=127,
        vote_average=7.3,
        vote_count=9000,
        genres=["Horror", "Mystery", "Thriller"],
        overview="Nach dem Tod der Großmutter wird eine Familie von unheimlichen Ereignissen verfolgt.",
        overview_en="After the grandmother's death, a family is haunted by sinister events.",
    ),
    dict(
        id=530385,
        title="Midsommar",
        original_title="Midsommar",
        year=2019,
        runtime=148,
        vote_average=7.1,
        vote_count=8000,
        genres=["Horror", "Drama", "Mystery"],
        overview="Eine Gruppe Freunde gerät auf einem schwedischen Mittsommerfest in einen Kult.",
        overview_en="A group of friends gets drawn into a cult at a Swedish midsummer festival.",
    ),
]


def film(row: dict, deutsch: bool) -> Movie:
    """A seed row as a catalogue film, in German or English (its genre names are the same in both)."""
    return Movie(
        id=row["id"],
        media_type="movie",
        title=row["title"] if deutsch else row["original_title"],
        original_title=row["original_title"],
        overview=row["overview"] if deutsch else row["overview_en"],
        release_date=f"{row['year']}-01-01",
        year=row["year"],
        runtime=row["runtime"],
        vote_average=row["vote_average"],
        vote_count=row["vote_count"],
        popularity=float(row["vote_count"]) / 100,
        genres=json.dumps(row["genres"]),
        is_canon=True,
    )


def seed_if_empty() -> int:
    deutsch = settings.tmdb_language.lower().startswith("de")
    with Session(engine) as db:
        if db.exec(select(Movie).limit(1)).first():
            return 0
        for row in SEED:
            db.add(film(row, deutsch))
        db.commit()
        return len(SEED)
