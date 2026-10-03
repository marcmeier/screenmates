from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import tmdb
from .config import settings
from .db import init_db
from .routers import catalog, features, kino, lists, misc, users, watched
from .seed import seed_if_empty

__version__ = "0.4.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_empty()
    await tmdb.startup()
    yield
    await tmdb.shutdown()


app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(tmdb.TMDBError)
async def tmdb_error(_: Request, exc: tmdb.TMDBError):
    return JSONResponse({"detail": str(exc)}, status_code=502)


for r in (catalog.router, users.router, watched.router, lists.router, features.router, misc.router, kino.router):
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
