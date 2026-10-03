"""„Wem gefällt's?": how much someone will like a film, from their own stars.

Per person, a small regularised regression (kernel ridge) learns what their
stars depend on: TMDB keywords ("slasher", "folk horror", …), genres, decade,
TMDB score and film series. A new film is then rated by what it has in common
with the films that person rated.

Measured on real TMDB films with simulated tastes (docs/PROGNOSE.md): with
about 10 ratings no method beats "the person's average"; from about 25 ratings
this one is up to 20 % closer for tastes that follow quality, era or
subgenre (slasher fans stay hard: too few slashers among 25 random films).
Hence the minimum below and the honest labels.

Every prediction names the most similar film the person rated the same way.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field

MIN_BEWERTUNGEN = 8  # below this a guess is no better than the average
TENDENZ_AB = 25  # from here on the guess is measurably better than the average
MAX_BEWERTUNGEN = 150  # newest ratings only; keeps the solve fast

# Feature weights and regularisation, chosen by the backtest in docs/PROGNOSE.md.
STICHWORT, GENRE, JAHRZEHNT, NOTE, REIHE = 0.6, 0.3, 0.6, 0.9, 1.5
LAMBDA = 2.5


@dataclass(frozen=True)
class Film:
    id: int
    titel: str = ""
    jahr: int | None = None
    note: float = 0.0  # TMDB vote average
    genres: frozenset[str] = field(default_factory=frozenset)
    stichworte: frozenset[str] = field(default_factory=frozenset)
    reihe: str = ""

    @classmethod
    def aus(cls, m) -> Film:
        return cls(
            id=m.id,
            titel=m.title,
            jahr=m.year,
            note=m.vote_average or 0.0,
            genres=frozenset(json.loads(m.genres or "[]")),
            stichworte=frozenset(json.loads(m.keywords or "[]")),
            reihe=m.collection or "",
        )


def merkmale(f: Film, bekannt: Counter | None = None) -> dict[str, float]:
    """Feature vector. With `bekannt`, keywords only count if at least two rated
    films share them: a keyword seen once teaches nothing but noise."""
    m = {f"k:{k}": STICHWORT for k in f.stichworte if bekannt is None or bekannt[k] >= 2}
    m |= {f"g:{g}": GENRE for g in f.genres}
    if f.jahr:
        dekade = f.jahr // 10 * 10
        # neighbouring decades count half: 1979 and 1981 are close
        m |= {f"d:{dekade - 10}": JAHRZEHNT / 2, f"d:{dekade + 10}": JAHRZEHNT / 2, f"d:{dekade}": JAHRZEHNT}
    if f.note:
        m["note"] = (f.note - 6.5) * NOTE
    if f.reihe:
        m[f"r:{f.reihe}"] = REIHE
    return m


def _dot(x: dict[str, float], y: dict[str, float]) -> float:
    if len(x) > len(y):
        x, y = y, x
    return sum(v * y.get(k, 0.0) for k, v in x.items())


def _loesen(a: list[list[float]], b: list[float]) -> list[float]:
    """Solve a·x = b for a symmetric positive definite a (Cholesky)."""
    n = len(b)
    unten = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = a[i][j] - sum(unten[i][k] * unten[j][k] for k in range(j))
            unten[i][j] = s**0.5 if i == j else s / unten[j][j]
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(unten[i][k] * y[k] for k in range(i))) / unten[i][i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(unten[k][i] * x[k] for k in range(i + 1, n))) / unten[i][i]
    return x


@dataclass
class Prognose:
    wert: float  # 1..5
    sicherheit: str  # "tendenz" | "erste tendenz"
    weil: tuple[Film, float] | None  # rated film that moved the guess most, and its stars


def vorhersage(ziel: Film, eigene: list[tuple[Film, float]]) -> Prognose | None:
    """Predict stars for `ziel` from someone's ratings [(film, stars)], newest last."""
    eigene = [(f, s) for f, s in eigene if f.id != ziel.id][-MAX_BEWERTUNGEN:]
    if len(eigene) < MIN_BEWERTUNGEN:
        return None
    mu = sum(s for _, s in eigene) / len(eigene)
    bekannt = Counter(k for f, _ in eigene for k in f.stichworte)
    x = [merkmale(f, bekannt) for f, _ in eigene]
    kern = [[_dot(x[i], x[j]) + (LAMBDA if i == j else 0.0) for j in range(len(x))] for i in range(len(x))]
    alpha = _loesen(kern, [s - mu for _, s in eigene])
    z = merkmale(ziel, bekannt)
    wert = min(5.0, max(1.0, mu + sum(a * _dot(z, xi) for a, xi in zip(alpha, x, strict=True))))
    # The reason shown to people: the most similar film they rated in the same
    # direction (the regression's largest term is often just an unusual film).
    # Similar means the same kind of film; the TMDB score says "good", not "alike".
    richtung = 1 if wert >= mu else -1
    art = [{k: v for k, v in xi.items() if k != "note"} for xi in x]
    za = {k: v for k, v in z.items() if k != "note"}
    laenge = _dot(za, za) ** 0.5 or 1.0

    def passend(k: int) -> float:
        if (eigene[k][1] - mu) * richtung <= 0:
            return 0.0
        return _dot(za, art[k]) / (laenge * (_dot(art[k], art[k]) ** 0.5 or 1.0))

    i = max(range(len(eigene)), key=passend)
    # Close to their average there is nothing to explain.
    weil = eigene[i] if abs(wert - mu) >= 0.35 and passend(i) >= 0.15 else None
    return Prognose(wert, "tendenz" if len(eigene) >= TENDENZ_AB else "erste tendenz", weil)
