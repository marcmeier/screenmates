"""Achievements ("Erfolge"): what counts, how much it's worth, and who has what.

Modelled on Xbox (points per achievement, tiers, secret achievements, unlock
pop-ups) and Steam (rarity, progress, levels from points, a showcase).

Rules against farming - the point of most of this module:

- Points only come from achievements, never per action. Tiers (1, 10, 25 …)
  cap what repetition can earn.
- Everything is counted from the current state, and only distinct things:
  deleting and re-adding, or changing a rating, earns nothing new.
- Giving likes or votes is never rewarded. What counts is receiving them from
  *different other* people; your own never count.
- A movie night only counts when it is *confirmed*: at least two
  participants, someone other than you among them has rated or commented it,
  and it wasn't entered more than two days after the fact. Ratings and
  comments only count on such evenings, comments from 20 characters, one per
  evening, at most three per day.
- Unlocks are permanent (like on Xbox/Steam). Admins can withdraw one; a
  withdrawn achievement stays withdrawn.
- Everything that already existed when achievements were introduced counts as
  it is, once (`AppMeta.erfolge_seit`).
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session as DBSession
from sqlmodel import col, select

from .models import (
    Abend,
    Abo,
    AppMeta,
    Ereignis,
    Erfolg,
    Feature,
    FeatureVote,
    Movie,
    NoteHeart,
    User,
    Watched,
    WatchedNote,
    WatchedParticipant,
    WatchedRating,
    now,
)

BERLIN = ZoneInfo("Europe/Berlin")
PUNKTE = {1: 10, 2: 25, 3: 50, 4: 100}  # bronze, silver, gold, platinum
STUFEN = {1: "bronze", 2: "silber", 3: "gold", 4: "platin"}
NACHTRAG = timedelta(days=2)  # entered later than this after the evening: doesn't count
KOMMENTAR_MIN = 20
KOMMENTARE_PRO_TAG = 3


@dataclass(frozen=True)
class Def:
    key: str
    familie: str
    name: str
    text: str
    emoji: str
    stufe: int
    ziel: int = 1
    geheim: bool = False
    kategorie: str = "Filmabend"

    @property
    def punkte(self) -> int:
        return PUNKTE[self.stufe]


def _reihe(familie, emoji, kategorie, texte, stufen):
    """A tiered family: [(name, goal), …] → bronze, silver, gold (, platinum).

    `texte` is (singular, plural); the plural gets the goal as {n}.
    """
    eins, viele = texte
    return [
        Def(
            f"{familie}-{i}",
            familie,
            name,
            eins if ziel == 1 else viele.format(n=ziel),
            emoji,
            i,
            ziel,
            kategorie=kategorie,
        )
        for i, (name, ziel) in enumerate(stufen, 1)
    ]


KATALOG: list[Def] = [
    *_reihe(
        "stammgast",
        "🛋️",
        "Filmabend",
        ("Bei einem bestätigten Filmabend dabei", "Bei {n} bestätigten Filmabenden dabei"),
        [("Erster Abend", 1), ("Stammgast", 5), ("Inventar", 15), ("Teil der Couch", 40)],
    ),
    *_reihe(
        "gastgeber",
        "🏠",
        "Filmabend",
        ("Einen Termin gesetzt, und der Abend fand statt", "{n}× einen Termin gesetzt, und der Abend fand statt"),
        [("Gastgeber", 1), ("Partyplaner", 5), ("Hausherr", 15)],
    ),
    *_reihe(
        "treffer",
        "🎯",
        "Filmabend",
        ("Ein eigener Vorschlag wurde gemeinsam geschaut", "{n} eigene Vorschläge wurden gemeinsam geschaut"),
        [("Volltreffer", 1), ("Geschmackssicher", 5), ("Trendsetter", 15)],
    ),
    *_reihe(
        "kritiker",
        "✍️",
        "Mitreden",
        ("Einen Film nach einem Filmabend bewertet", "{n} Filme nach Filmabenden bewertet"),
        [("Erste Kritik", 1), ("Kritiker", 10), ("Feuilleton", 30), ("Goldene Feder", 75)],
    ),
    *_reihe(
        "gaestebuch",
        "📖",
        "Mitreden",
        (
            "Einen Gästebuch-Eintrag zu einem Filmabend geschrieben (ab 20 Zeichen)",
            "{n} Gästebuch-Einträge zu Filmabenden (ab 20 Zeichen)",
        ),
        [("Erster Eintrag", 1), ("Plaudertasche", 10), ("Chronist", 40)],
    ),
    *_reihe(
        "herz",
        "❤️",
        "Mitreden",
        ("Ein Herz bekommen", "Herzen von {n} verschiedenen Leuten bekommen"),
        [("Gemocht", 3), ("Beliebt", 6), ("Herzensbrecher", 10)],
    ),
    *_reihe(
        "ideen",
        "💡",
        "Mitreden",
        (
            "Ein Wunsch wurde umgesetzt oder von drei anderen unterstützt",
            "{n} Wünsche umgesetzt oder von drei anderen unterstützt",
        ),
        [("Ideengeber", 1), ("Visionär", 3), ("Architekt", 10)],
    ),
    *_reihe(
        "regie",
        "🎬",
        "Kino",
        (
            "Eine Vorstellung mit mindestens zwei Zuschauenden gesendet",
            "{n} Vorstellungen mit mindestens zwei Zuschauenden gesendet",
        ),
        [("Auf Sendung", 1), ("Programmkino", 5), ("Intendanz", 15)],
    ),
    *_reihe(
        "kino",
        "🎟️",
        "Kino",
        ("Eine Vorstellung im Kino geschaut", "{n} Vorstellungen im Kino geschaut"),
        [("Erste Reihe", 1), ("Kinogänger", 5), ("Dauerkarte", 20)],
    ),
    Def("bild", "bild", "Gesicht zeigen", "Ein Profilbild hochgeladen", "📸", 1, kategorie="Profil"),
    Def(
        "schutz",
        "schutz",
        "Sicher ist sicher",
        "Den eigenen Namen mit einem Film-Passwort geschützt",
        "🔐",
        1,
        kategorie="Profil",
    ),
    Def("abos", "abos", "Abo-Profi", "Die eigenen Streamingdienste eingetragen", "📺", 1, kategorie="Profil"),
    Def(
        "nachteule",
        "nachteule",
        "Nachteule",
        "Einen Filmabend nach Mitternacht beendet",
        "🦉",
        2,
        geheim=True,
        kategorie="Geheim",
    ),
    Def(
        "marathon",
        "marathon",
        "Marathon",
        "Drei Filme an einem Tag gemeinsam geschaut",
        "🏃",
        3,
        geheim=True,
        kategorie="Geheim",
    ),
    Def(
        "zeitreise",
        "zeitreise",
        "Zeitreise",
        "Gemeinsam einen Film von vor 1960 geschaut",
        "⏳",
        2,
        geheim=True,
        kategorie="Geheim",
    ),
    Def(
        "gourmet",
        "gourmet",
        "Genre-Gourmet",
        "Bei Filmabenden Filme aus sechs Genres geschaut",
        "🍱",
        2,
        geheim=True,
        kategorie="Geheim",
    ),
    Def(
        "einstimmig",
        "einstimmig",
        "Einstimmig",
        "Mindestens drei haben einen Film genau gleich bewertet",
        "🤝",
        2,
        geheim=True,
        kategorie="Geheim",
    ),
    Def("jubilaeum", "jubilaeum", "Jubiläum", "Seit einem Jahr dabei", "🎂", 3, geheim=True, kategorie="Geheim"),
]
NACH_KEY = {d.key: d for d in KATALOG}

# Levels from points, like Steam: each level needs a bit more than the one before.
TITEL = [
    (1, "Popcorn-Neuling"),
    (3, "Filmfan"),
    (5, "Cineast"),
    (7, "Kritikerliebling"),
    (9, "Regielegende"),
    (11, "Hall of Fame"),
]


def level(punkte: int) -> int:
    n = 1
    while 12.5 * (n + 1) * n <= punkte:
        n += 1
    return n


def level_ab(n: int) -> int:
    return int(12.5 * n * (n - 1))


def titel(lvl: int) -> str:
    return [t for ab, t in TITEL if lvl >= ab][-1]


# --- what everyone has done ------------------------------------------------------


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _tag(dt: datetime) -> date:
    return _aware(dt).astimezone(BERLIN).date()


def stand(db: DBSession) -> dict[int, Counter]:
    """For every approved user: how far they are in each family (and the secret ones as 0/1)."""
    meta = db.get(AppMeta, 1)
    seit = _aware(meta.erfolge_seit) if meta and meta.erfolge_seit else _aware(now())
    jetzt = _aware(now())
    users = db.exec(select(User).where(col(User.freigegeben))).all()

    watched = {w.id: w for w in db.exec(select(Watched).where(col(Watched.hidden).is_(False))).all()}
    teil: dict[int, set[int]] = defaultdict(set)
    for wid, uid in db.exec(select(WatchedParticipant.watched_id, WatchedParticipant.user_id)).all():
        teil[wid].add(uid)
    bewertet: dict[int, dict[int, int]] = defaultdict(dict)
    for wid, uid, stars in db.exec(select(WatchedRating.watched_id, WatchedRating.user_id, WatchedRating.stars)).all():
        bewertet[wid][uid] = stars
    notizen = db.exec(select(WatchedNote)).all()
    kommentiert: dict[int, set[int]] = defaultdict(set)
    for n in notizen:
        if n.user_id is not None:
            kommentiert[n.watched_id].add(n.user_id)
    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({w.movie_id for w in watched.values()})))}

    def alt(w: Watched) -> bool:
        return _aware(w.created_at) < seit

    def echt(w: Watched, u: int) -> bool:
        """A real evening from u's point of view: confirmed by someone else who was there."""
        if alt(w):
            return True
        if len(teil[w.id]) < 2 or _aware(w.created_at) - _aware(w.watched_at) > NACHTRAG:
            return False
        if _aware(w.watched_at) > jetzt + timedelta(hours=1):
            return False
        andere = (set(bewertet[w.id]) | kommentiert[w.id]) & teil[w.id] - {u}
        return bool(andere)

    def abend_fand_statt(tag: date) -> bool:
        return any(
            len(teil[w.id]) >= 2 and abs((_tag(w.watched_at) - tag).days) <= 1 and any(echt(w, p) for p in teil[w.id])
            for w in watched.values()
        )

    herzen: dict[int, set[int]] = defaultdict(set)  # author -> distinct other people who hearted
    autor = {n.id: n.user_id for n in notizen}
    for nid, uid in db.exec(select(NoteHeart.note_id, NoteHeart.user_id)).all():
        a = autor.get(nid)
        if a is not None and a != uid:
            herzen[a].add(uid)

    stimmen: dict[int, set[int]] = defaultdict(set)
    for fid, uid in db.exec(select(FeatureVote.feature_id, FeatureVote.user_id)).all():
        stimmen[fid].add(uid)
    ideen: Counter = Counter()
    for f in db.exec(select(Feature)).all():
        if f.user_id is not None and (f.done or len(stimmen[f.id] - {f.user_id}) >= 3):
            ideen[f.user_id] += 1

    ereignisse = db.exec(select(Ereignis)).all()
    termine: dict[int, set[date]] = defaultdict(set)
    regie: dict[int, set[str]] = defaultdict(set)
    kino: dict[int, set[str]] = defaultdict(set)
    treffer: dict[int, set[int]] = defaultdict(set)
    for e in ereignisse:
        if e.user_id is None:
            continue
        if e.typ == "termin" and e.bezug:
            termine[e.user_id].add(date.fromisoformat(e.bezug))
        elif e.typ == "kino_gesendet":
            regie[e.user_id].add(e.bezug)
        elif e.typ == "kino_geschaut":
            kino[e.user_id].add(e.bezug)
        elif e.typ == "treffer" and e.bezug:
            treffer[e.user_id].add(int(e.bezug))
    for abend in db.exec(select(Abend)).all():  # one per group; before the launch only the current one is known
        if abend.termin and abend.gesetzt_von and abend.gesetzt_am and _aware(abend.gesetzt_am) < seit:
            termine[abend.gesetzt_von].add(_tag(abend.termin))

    abos = set(db.exec(select(Abo.user_id)).all())

    out: dict[int, Counter] = {}
    for user in users:
        u = user.id
        c: Counter = Counter()
        meine = [w for w in watched.values() if u in teil[w.id] and echt(w, u)]
        tage = Counter(_tag(w.watched_at) for w in meine)
        c["stammgast"] = len(tage)
        c["kritiker"] = sum(1 for w in watched.values() if u in bewertet[w.id] and echt(w, u))
        pro_tag: Counter = Counter()
        gezaehlt: set[int] = set()
        for n in sorted(notizen, key=lambda n: _aware(n.created_at)):
            w = watched.get(n.watched_id)
            if n.user_id != u or w is None or n.watched_id in gezaehlt or len(n.text.strip()) < KOMMENTAR_MIN:
                continue
            if not echt(w, u):
                continue
            tag = _tag(n.created_at)
            if pro_tag[tag] < KOMMENTARE_PRO_TAG or _aware(n.created_at) < seit:
                pro_tag[tag] += 1
                gezaehlt.add(n.watched_id)
        c["gaestebuch"] = len(gezaehlt)
        c["herz"] = len(herzen[u])
        c["ideen"] = ideen[u]
        c["gastgeber"] = sum(1 for t in termine[u] if abend_fand_statt(t))
        c["regie"] = len(regie[u])
        c["kino"] = len(kino[u])
        c["treffer"] = sum(1 for wid in treffer[u] if wid in watched and any(echt(watched[wid], p) for p in teil[wid]))
        c["bild"] = int(bool(user.bild))
        c["schutz"] = int(user.schutz_movie_id is not None)
        c["abos"] = int(u in abos)
        c["nachteule"] = int(any(_aware(w.watched_at).astimezone(BERLIN).hour < 5 for w in meine))
        c["marathon"] = int(any(n >= 3 for n in tage.values()))
        c["zeitreise"] = int(any((filme.get(w.movie_id) and (filme[w.movie_id].year or 9999) < 1960) for w in meine))
        genres = {g for w in meine if w.movie_id in filme for g in json.loads(filme[w.movie_id].genres or "[]")}
        c["gourmet"] = int(len(genres) >= 6)
        c["einstimmig"] = int(
            any(
                u in bewertet[w.id] and len(bewertet[w.id]) >= 3 and len(set(bewertet[w.id].values())) == 1
                for w in watched.values()
                if echt(w, u)
            )
        )
        c["jubilaeum"] = int(jetzt - _aware(user.created_at) >= timedelta(days=365))
        out[u] = c
    return out


# --- unlocking -------------------------------------------------------------------

_zuletzt = 0.0
PAUSE = 5.0  # seconds between full evaluations


def pruefen(db: DBSession, *, sofort: bool = False) -> None:
    """Unlock whatever has been reached. Cheap enough for a group, throttled anyway."""
    global _zuletzt
    if not sofort and time.monotonic() - _zuletzt < PAUSE:
        return
    _zuletzt = time.monotonic()
    meta = db.get(AppMeta, 1) or AppMeta(id=1)
    erster_lauf = not meta.erfolge_geprueft
    vorhanden = {(e.user_id, e.schluessel) for e in db.exec(select(Erfolg)).all()}
    jetzt = now()
    for uid, c in stand(db).items():
        for d in KATALOG:
            if (uid, d.key) not in vorhanden and c[d.familie] >= d.ziel:
                db.add(Erfolg(user_id=uid, schluessel=d.key, am=jetzt, rueckwirkend=erster_lauf))
    if erster_lauf:
        meta.erfolge_geprueft = True
        db.add(meta)
    db.commit()


def freigeschaltet(db: DBSession) -> dict[int, dict[str, Erfolg]]:
    out: dict[int, dict[str, Erfolg]] = defaultdict(dict)
    for e in db.exec(select(Erfolg).where(col(Erfolg.entzogen).is_(False))).all():
        if e.schluessel in NACH_KEY:
            out[e.user_id][e.schluessel] = e
    return out


def punkte(erfolge: dict[str, Erfolg]) -> int:
    return sum(NACH_KEY[k].punkte for k in erfolge)


def levels(db: DBSession) -> dict[int, int]:
    return {uid: level(punkte(e)) for uid, e in freigeschaltet(db).items()}


def protokoll(db: DBSession, typ: str, user_id: int | None, bezug: str = "") -> None:
    """Record something that can't be read from the data later (no commit)."""
    if user_id is not None:
        db.add(Ereignis(typ=typ, user_id=user_id, bezug=bezug))
