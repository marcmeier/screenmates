import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import erfolge, push, tmdb
from .config import settings
from .db import engine, init_db
from .gruppen import kontext
from .routers import (
    abend,
    admin,
    catalog,
    einladungen,
    features,
    gastgeber,
    glocke,
    gruppen,
    kalender,
    kino,
    kinochat,
    kiste,
    lists,
    live,
    misc,
    profilbild,
    reset,
    rueckblick,
    statistik,
    ueber,
    umfrage,
    users,
    watched,
    zugang,
)
from .routers import erfolge as erfolge_api
from .routers import push as push_api
from .seed import seed_if_empty
from .sprache import SprachMiddleware, tr

__version__ = "0.21.2"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    # Achievements: the first check right away, so only history counts as retroactive.
    with Session(engine) as db:
        erfolge.pruefen(db, sofort=True)
    await tmdb.startup()
    # The Kino's traffic for the statistics: MediaMTX forgets sessions, so count along.
    zaehlen = asyncio.create_task(statistik.kino_mitzaehlen()) if settings.kino_enabled else None
    erinnern = asyncio.create_task(push.erinnern())  # push reminders on the day of the movie night
    yield
    erinnern.cancel()
    if zaehlen:
        zaehlen.cancel()
    await tmdb.shutdown()


# Invite-only: the whole API is closed to browsers without an invitation or a session.
app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
    dependencies=[Depends(zugang.zugang_pruefen), Depends(kontext)],
)

# Live updates: successful writes bump counters every open app polls (routers/live.py).
app.middleware("http")(live.mitzaehlen)

# The app's language (X-Sprache) for texts the server writes.
app.add_middleware(SprachMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Errors in the language of the app that asked (see sprache.py).
@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException):
    detail = tr(exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(tmdb.TMDBError)
async def tmdb_error(_: Request, exc: tmdb.TMDBError):
    return JSONResponse({"detail": str(exc)}, status_code=502)


for r in (
    catalog.router,
    users.router,
    watched.router,
    lists.router,
    features.router,
    misc.router,
    kinochat.router,
    kino.router,
    abend.router,
    zugang.router,
    admin.router,
    profilbild.router,
    erfolge_api.router,
    gruppen.router,
    einladungen.router,
    kiste.router,
    gastgeber.router,
    live.router,
    statistik.router,
    ueber.router,
    umfrage.router,
    kalender.router,
    push_api.router,
    rueckblick.router,
    reset.router,
    glocke.router,
):
    app.include_router(r)


# Serve the built frontend if present (production: one origin, no CORS needed).
_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file = (_dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(_dist):
            return FileResponse(file)
        return FileResponse(_dist / "index.html")
