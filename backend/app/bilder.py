"""Profile pictures: one small square WebP per person, stored next to the database.

Uploads are decoded with Pillow and re-encoded from scratch, so nothing of the
original file survives: no EXIF (GPS position of a phone photo, camera,
date), no hidden payloads. Phone photos are turned upright first.
"""

from __future__ import annotations

import io
import secrets
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .config import settings

MAX_BYTES = 5 * 1024 * 1024  # upload limit; the browser shrinks photos before sending
SEITE = 256  # px, square
FORMATE = {"JPEG", "PNG", "WEBP", "GIF"}
# Refuse decompression bombs: a tiny file that claims to be gigapixels.
MAX_PIXEL = 40_000_000


class BildFehler(ValueError):
    pass


def ordner() -> Path:
    d = settings.media_path / "profilbilder"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pfad(user_id: int, token: str) -> Path:
    return ordner() / f"{user_id}-{token}.webp"


def verarbeiten(data: bytes) -> bytes:
    """Any common image in, a square SEITE px WebP out (centre crop, a bit above middle for faces)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(data))
            if im.format not in FORMATE:
                raise BildFehler("Bitte ein JPG-, PNG-, WebP- oder GIF-Bild.")
            if im.width * im.height > MAX_PIXEL:
                raise BildFehler("Das Bild ist zu groß.")
            im = ImageOps.exif_transpose(im)
            im = im.convert("RGBA" if "A" in im.getbands() or "transparency" in im.info else "RGB")
            im = ImageOps.fit(im, (SEITE, SEITE), Image.Resampling.LANCZOS, centering=(0.5, 0.4))
            out = io.BytesIO()
            im.save(out, "WEBP", quality=82, method=6)
    except BildFehler:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError):
        raise BildFehler("Das Bild konnte nicht gelesen werden.") from None
    return out.getvalue()


def speichern(user_id: int, webp: bytes) -> str:
    """Write a new file and return its token (part of the URL, so caches never serve an old picture)."""
    token = secrets.token_hex(6)
    ziel = pfad(user_id, token)
    tmp = ziel.with_suffix(".tmp")
    tmp.write_bytes(webp)
    tmp.replace(ziel)
    return token


def loeschen(user_id: int, token: str) -> None:
    if token:
        pfad(user_id, token).unlink(missing_ok=True)
