"""The year in review: a group's film year in numbers ("screenmates Wrapped").

Everything comes from the chronicle of the active group (hidden entries left
out), by calendar year in the group's time: how many films and evenings, which genres and
decades, the best and the most disputed film, and a few friendly titles for the
people: who was there most, who rates strictest, who gets the most hearts.
Titles need a minimum of data (``MIN_PERSON`` ratings), so one 1-star rating
doesn't make anyone the harshest critic.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from statistics import mean

from fastapi import APIRouter, Depends
from sqlmodel import Session as DBSession
from sqlmodel import col, select

from ..db import get_session
from ..gruppen import aktive_gruppe
from ..models import (
    Ereignis,
    Kistenoeffnung,
    Movie,
    NoteHeart,
    Watched,
    WatchedNote,
    WatchedParticipant,
    WatchedRating,
)
from ..serialize import iso, movie_dict
from ..util import MONATE, WOCHENTAGE, utc
from ..zeitzone import zone

router = APIRouter(prefix="/api/rueckblick", tags=["rueckblick"])

MIN_FILM = 2  # ratings a film needs for best / worst / disputed
MIN_PERSON = 3  # ratings a person needs for strictest / most generous


def _tag(dt: datetime) -> date:
    return utc(dt).astimezone(zone()).date()


def _gesehen(db: DBSession, gid: int) -> list[Watched]:
    return list(
        db.exec(
            select(Watched).where(Watched.gruppe_id == gid, col(Watched.hidden).is_(False)).order_by(Watched.watched_at)
        ).all()
    )


@router.get("")
def years(gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    jahre = sorted({_tag(w.watched_at).year for w in _gesehen(db, gid)}, reverse=True)
    return {"jahre": jahre, "jetzt": datetime.now(zone()).year}


def _bester(werte: dict, umgekehrt: bool = False):
    """The key with the highest (lowest) value; on a tie the first one."""
    if not werte:
        return None
    return (min if umgekehrt else max)(werte, key=lambda k: werte[k])


def _serie(tage: list[date]) -> int:
    """The longest run of consecutive weeks with at least one movie night."""
    wochen = sorted({t - timedelta(days=t.weekday()) for t in tage})
    beste = lauf = 1 if wochen else 0
    for a, b in pairwise(wochen):
        lauf = lauf + 1 if (b - a).days == 7 else 1
        beste = max(beste, lauf)
    return beste


@router.get("/{jahr}")
def year_in_review(jahr: int, gid: int = Depends(aktive_gruppe), db: DBSession = Depends(get_session)):
    ws = [w for w in _gesehen(db, gid) if _tag(w.watched_at).year == jahr]
    if not ws:
        return {"jahr": jahr, "filme": 0}
    ids = [w.id for w in ws]
    filme = {m.id: m for m in db.exec(select(Movie).where(col(Movie.id).in_({w.movie_id for w in ws}))).all()}
    ws = [w for w in ws if w.movie_id in filme]
    film = {w.id: filme[w.movie_id] for w in ws}

    def eintrag(w: Watched, **extra) -> dict:
        return {"movie": movie_dict(film[w.id]), "am": iso(w.watched_at), **extra}

    tage = sorted({_tag(w.watched_at) for w in ws})
    minuten = sum(film[w.id].runtime or 0 for w in ws)
    genres = Counter(g for w in ws for g in json.loads(film[w.id].genres or "[]"))
    jahrzehnte = Counter((film[w.id].year // 10) * 10 for w in ws if film[w.id].year)
    monate = Counter(_tag(w.watched_at).month for w in ws)
    wochentage = Counter(t.weekday() for t in tage)

    sterne: dict[int, dict[int, int]] = defaultdict(dict)
    for wid, uid, s in db.exec(
        select(WatchedRating.watched_id, WatchedRating.user_id, WatchedRating.stars).where(
            col(WatchedRating.watched_id).in_(ids)
        )
    ).all():
        if s:
            sterne[wid][uid] = s
    teil: dict[int, set[int]] = defaultdict(set)
    for wid, uid in db.exec(
        select(WatchedParticipant.watched_id, WatchedParticipant.user_id).where(
            col(WatchedParticipant.watched_id).in_(ids)
        )
    ).all():
        teil[wid].add(uid)

    bewertet = [w for w in ws if len(sterne[w.id]) >= MIN_FILM]
    schnitt = {w.id: mean(sterne[w.id].values()) for w in bewertet}
    spanne = {w.id: max(sterne[w.id].values()) - min(sterne[w.id].values()) for w in bewertet}
    nach_id = {w.id: w for w in ws}

    filme_out: dict[str, dict | None] = {"bester": None, "schlechtester": None, "umstritten": None, "einig": None}
    if schnitt:
        b = _bester(schnitt)
        filme_out["bester"] = eintrag(nach_id[b], sterne=round(schnitt[b], 1))
        s = _bester(schnitt, umgekehrt=True)
        if s != b and schnitt[s] < schnitt[b]:
            filme_out["schlechtester"] = eintrag(nach_id[s], sterne=round(schnitt[s], 1))
        u = _bester(spanne)
        if spanne[u] >= 2:
            st = sterne[u]
            filme_out["umstritten"] = eintrag(
                nach_id[u], hoch=_bester(st), tief=_bester(st, umgekehrt=True), spanne=spanne[u]
            )
        einig = [w for w in bewertet if len(sterne[w.id]) >= 3 and spanne[w.id] == 0]
        if einig:
            filme_out["einig"] = eintrag(einig[0], sterne=next(iter(sterne[einig[0].id].values())))

    mit_laenge = [w for w in ws if film[w.id].runtime]
    mit_jahr = [w for w in ws if film[w.id].year]

    # People: who was there, who rated how, who wrote and got hearts.
    abende: dict[int, set[date]] = defaultdict(set)
    for w in ws:
        for uid in teil[w.id]:
            abende[uid].add(_tag(w.watched_at))
    meine_sterne: dict[int, list[int]] = defaultdict(list)
    for st in sterne.values():
        for uid, s in st.items():
            meine_sterne[uid].append(s)
    notizen = db.exec(
        select(WatchedNote).where(col(WatchedNote.watched_id).in_(ids), WatchedNote.geloescht == "")
    ).all()
    kommentare = Counter(n.user_id for n in notizen if n.user_id is not None)
    autor = {n.id: n.user_id for n in notizen}
    herzen: Counter = Counter()
    for nid, uid in db.exec(
        select(NoteHeart.note_id, NoteHeart.user_id).where(col(NoteHeart.note_id).in_(list(autor)))
    ).all():
        if autor.get(nid) is not None and autor[nid] != uid:
            herzen[autor[nid]] += 1
    treffer = Counter(
        e.user_id
        for e in db.exec(
            select(Ereignis).where(Ereignis.typ == "treffer", col(Ereignis.bezug).in_([str(i) for i in ids]))
        )
        if e.user_id is not None
    )
    schnitte = {uid: mean(v) for uid, v in meine_sterne.items() if len(v) >= MIN_PERSON}

    def titel(werte: dict, umgekehrt: bool = False, wert=lambda x: x) -> dict | None:
        k = _bester(werte, umgekehrt)
        return {"user_id": k, "wert": wert(werte[k])} if k is not None else None

    streng = titel(schnitte, umgekehrt=True, wert=lambda x: round(x, 1))
    mild = titel(schnitte, wert=lambda x: round(x, 1))
    leute = {
        "stammgast": titel({u: len(t) for u, t in abende.items()}),
        "streng": streng,
        "grosszuegig": mild if mild and streng and mild["user_id"] != streng["user_id"] else None,
        "plaudertasche": titel(dict(kommentare)),
        "herzensbrecher": titel(dict(herzen)),
        "trendsetter": titel(dict(treffer)),
    }

    kisten = sum(
        1
        for k in db.exec(select(Kistenoeffnung).where(Kistenoeffnung.gruppe_id == gid)).all()
        if _tag(k.start).year == jahr and utc(k.start) <= datetime.now(UTC)
    )
    alle_sterne = [s for st in sterne.values() for s in st.values()]
    top_jahrzehnt = jahrzehnte.most_common(1)
    top_monat = monate.most_common(1)[0]
    top_tag = wochentage.most_common(1)[0]
    return {
        "jahr": jahr,
        "filme": len(ws),
        "abende": len(tage),
        "minuten": minuten,
        "genres": [{"name": g, "anzahl": n} for g, n in genres.most_common(5)],
        "jahrzehnt": {"jahrzehnt": top_jahrzehnt[0][0], "anzahl": top_jahrzehnt[0][1]} if top_jahrzehnt else None,
        "monat": {"name": MONATE[top_monat[0] - 1], "nr": top_monat[0], "anzahl": top_monat[1]},
        "wochentag": {"name": WOCHENTAGE[top_tag[0]], "nr": top_tag[0], "anzahl": top_tag[1]},
        "serie": _serie(tage),
        "kisten": kisten,
        "bewertungen": len(alle_sterne),
        "schnitt": round(mean(alle_sterne), 1) if alle_sterne else None,
        "kommentare": len(notizen),
        "herzen": sum(herzen.values()),
        "leute": len(abende),
        "erster": eintrag(ws[0]),
        "letzter": eintrag(ws[-1]) if len(ws) > 1 else None,
        "laengster": eintrag(max(mit_laenge, key=lambda w: film[w.id].runtime)) if mit_laenge else None,
        "kuerzester": eintrag(min(mit_laenge, key=lambda w: film[w.id].runtime)) if len(mit_laenge) > 1 else None,
        "aeltester": eintrag(min(mit_jahr, key=lambda w: film[w.id].year)) if mit_jahr else None,
        **filme_out,
        "titel": leute,
    }
