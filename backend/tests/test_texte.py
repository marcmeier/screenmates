"""Every German text the server writes for people has an English version (texte_en.EN).

Texts stay German in the code and are looked up in EN by `tr()`; a missing entry would
silently show German in the English app. This finds them: error messages, `tr(...)` calls,
and the titles and texts of push messages.
"""

import ast
import re
from pathlib import Path

from app.texte_en import EN

APP = Path(__file__).resolve().parents[1] / "app"
# Texts without words to translate.
SPRACHLOS = {"{name}: {wann}{notiz}", "{text}", "🎬 screenmates"}


def _texte():
    for path in APP.rglob("*.py"):
        if path.name == "texte_en.py":
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name == "HTTPException" and len(node.args) >= 2:
                kandidaten = [node.args[1]]
            elif name in ("tr", "BildFehler", "KIError", "TMDBError"):
                kandidaten = node.args[:1]
            elif name == "an" and len(node.args) >= 5:  # push.an(db, uids, art, titel, text)
                kandidaten = node.args[3:5]
            else:
                continue
            for k in kandidaten:
                werte = [k] if isinstance(k, ast.Constant) else [k.body, k.orelse] if isinstance(k, ast.IfExp) else []
                for w in werte:
                    if isinstance(w, ast.Constant) and isinstance(w.value, str):
                        yield f"{path.name}:{node.lineno}", w.value


def test_every_server_text_has_an_english_version():
    fehlen = sorted({(wo, t) for wo, t in _texte() if t not in EN and t not in SPRACHLOS})
    assert fehlen == [], "add these to app/texte_en.py: " + "; ".join(f"{wo} {t!r}" for wo, t in fehlen)


def test_the_check_finds_something():
    texte = {t for _, t in _texte()}
    assert "Bitte zuerst einen Namen wählen." in texte and len(texte) > 100
    assert all(re.search(r"\w", t) for t in texte)
