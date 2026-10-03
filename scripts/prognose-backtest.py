"""Backtest for „Wem gefällt's?" (app/prognose.py) on real TMDB films.

Simulated people with a known taste rate random horror films (with noise);
each rating is hidden in turn and predicted from the others. The score is how
much closer the prediction gets than "the person's average".

    cd backend && .venv/bin/python ../scripts/prognose-backtest.py [cache.json]

Needs TMDB_API_KEY (backend/.env) for the first run; the films are cached.
"""

import asyncio
import json
import random
import statistics
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import tmdb
from app.prognose import Film, vorhersage

CACHE = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/screenmates-backtest-filme.json")


async def laden() -> list[dict]:
    """The 160 most voted horror films, with keywords."""
    await tmdb.startup()
    ids = []
    for seite in range(1, 9):
        d = await tmdb._get(
            "/discover/movie",
            {"with_genres": 27, "sort_by": "vote_count.desc", "page": seite},
        )
        ids += [r["id"] for r in d["results"]]
    filme = []
    for i in range(0, len(ids), 10):
        filme += await asyncio.gather(*(tmdb.details(x) for x in ids[i : i + 10]))
    await tmdb.shutdown()
    return [f for f in filme if f]


def hat(f: Film, *woerter: str) -> bool:
    return any(any(w in k for w in woerter) for k in f.stichworte)


# Simulated tastes: stars before noise and rounding. None = random stars.
GESCHMACK = {
    "Slasher": lambda f: (
        3 + 1.5 * hat(f, "slasher", "serial killer") - 1.2 * hat(f, "found footage", "demon", "possession")
    ),
    "Übernatürlich": lambda f: (
        2.6 + 1.6 * hat(f, "supernatural", "ghost", "demon", "possession", "haunted") - 1.0 * hat(f, "slasher", "gore")
    ),
    "Klassiker": lambda f: 2 + (2.2 if f.jahr and f.jahr < 1990 else 0) + 0.4 * (f.note - 7),
    "Qualität": lambda f: 3 + 1.1 * (f.note - 6.8),
    "Monster": lambda f: 2.5 + 1.8 * hat(f, "alien", "monster", "creature", "zombie", "virus"),
    "Zufall": None,
}


def gewinn(filme: list[Film], n: int, seed: int, personen: int = 5) -> dict[str, float]:
    rnd = random.Random(seed)
    out = {}
    for name, g in GESCHMACK.items():
        fehler_p, fehler_d = [], []
        for _ in range(personen):
            auswahl = rnd.sample(filme, n)
            sterne = [
                (
                    f,
                    rnd.randint(1, 5) if g is None else min(5, max(1, round(g(f) + rnd.gauss(0, 0.6)))),
                )
                for f in auswahl
            ]
            for i, (f, wahr) in enumerate(sterne):
                rest = sterne[:i] + sterne[i + 1 :]
                mittel = statistics.mean(s for _, s in rest)
                p = vorhersage(f, rest)
                fehler_p.append(abs((p.wert if p else mittel) - wahr))
                fehler_d.append(abs(mittel - wahr))
        out[name] = 1 - statistics.mean(fehler_p) / statistics.mean(fehler_d)
    return out


def main() -> None:
    if not CACHE.exists():
        CACHE.write_text(json.dumps(asyncio.run(laden())))
    filme = [
        Film.aus(
            SimpleNamespace(
                id=d["id"],
                title=d["title"],
                year=d["year"],
                vote_average=d["vote_average"],
                genres=d["genres"],
                keywords=d["keywords"],
                collection=d["collection"],
            )
        )
        for d in json.loads(CACHE.read_text())
    ]
    print(f"{len(filme)} Filme. Besser als der Durchschnitt der Person um:\n")
    print("| Bewertungen | " + " | ".join(GESCHMACK) + " |")
    print("|---" * (len(GESCHMACK) + 1) + "|")
    for n in (10, 25, 60):
        laeufe = [gewinn(filme, n, seed) for seed in (11, 12, 13)]
        print(
            f"| {n} | "
            + " | ".join(f"{100 * statistics.mean(lauf[k] for lauf in laeufe):+.0f} %" for k in GESCHMACK)
            + " |"
        )


if __name__ == "__main__":
    main()
