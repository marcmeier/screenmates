"""Seed catalogue so screenmates is usable before a TMDB key is configured.

Real TMDB ids are used so that, once a key is added and `/api/sync` (or a detail
fetch) runs, these rows upgrade in place with posters and full metadata."""

from __future__ import annotations

import json

from sqlmodel import Session, select

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
    ),
]


def seed_if_empty() -> int:
    with Session(engine) as db:
        if db.exec(select(Movie).limit(1)).first():
            return 0
        for row in SEED:
            db.add(
                Movie(
                    id=row["id"],
                    media_type="movie",
                    title=row["title"],
                    original_title=row["original_title"],
                    overview=row["overview"],
                    release_date=f"{row['year']}-01-01",
                    year=row["year"],
                    runtime=row["runtime"],
                    vote_average=row["vote_average"],
                    vote_count=row["vote_count"],
                    popularity=float(row["vote_count"]) / 100,
                    genres=json.dumps(row["genres"]),
                    is_canon=True,
                )
            )
        db.commit()
        return len(SEED)
