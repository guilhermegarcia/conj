"""Read-only access to the conjugation database."""

from __future__ import annotations

import gzip
import json
import os
import shutil
import sqlite3
import sys
import zlib
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from pathlib import Path

from .normalize import fold

PACKAGED = Path(__file__).parent / "data" / "conj.sqlite.gz"


def cache_dir() -> Path:
    if env := os.environ.get("XDG_CACHE_HOME"):
        return Path(env) / "conj"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "conj"
    return Path.home() / ".cache" / "conj"


def db_path() -> Path:
    """Path of the uncompressed database, unpacking the packaged copy if needed."""
    if env := os.environ.get("CONJ_DB"):
        return Path(env)
    if not PACKAGED.exists():
        raise FileNotFoundError(
            f"No verb database at {PACKAGED}. Build it with: uv run python -m conj.build"
        )
    stamp = PACKAGED.stat()
    target = cache_dir() / f"conj-{stamp.st_size}-{int(stamp.st_mtime)}.sqlite"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        for old in target.parent.glob("conj-*.sqlite"):
            old.unlink()
        tmp = target.with_suffix(".part")
        with gzip.open(PACKAGED, "rb") as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst)
        tmp.rename(target)
    return target


@dataclass
class Verb:
    id: int
    lang: str
    lemma: str
    score: int
    aux: list[str]
    glosses: list[str]
    heads: list[str]
    _blob: bytes = field(repr=False)

    @cached_property
    def paradigm(self) -> dict:
        return json.loads(zlib.decompress(self._blob))

    def cells_for(self, form: str) -> list[str]:
        """Paradigm cells ("IND.PRS:1s", "PTCP.PST") whose form folds to `form`."""
        key, out = fold(form), []
        for tense, val in self.paradigm.items():
            if isinstance(val, list):
                if any(fold(f) == key for f in val):
                    out.append(tense)
            else:
                out += [f"{tense}:{p}" for p, fs in val.items() if any(fold(f) == key for f in fs)]
        return out


class DB:
    def __init__(self, path: Path | None = None):
        path = path or db_path()
        self.con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)

    _COLS = "id, lang, lemma, score, aux, glosses, heads, paradigm"

    def _verb(self, row) -> Verb:
        id_, lang, lemma, score, aux, gl, heads, blob = row
        return Verb(id_, lang, lemma, score, json.loads(aux), json.loads(gl), json.loads(heads), blob)

    def get(self, lang: str, lemma: str) -> Verb | None:
        row = self.con.execute(
            f"SELECT {self._COLS} FROM lemma WHERE lang=? AND key=? ORDER BY lemma=? DESC, score DESC",
            (lang, fold(lemma), lemma),
        ).fetchone()
        return self._verb(row) if row else None

    def by_id(self, id_: int) -> Verb:
        return self._verb(self.con.execute(f"SELECT {self._COLS} FROM lemma WHERE id=?", (id_,)).fetchone())

    def reverse(self, form: str, lang: str | None = None) -> list[Verb]:
        """Verbs having `form` anywhere in their paradigm, most common first."""
        sql = (f"SELECT {', '.join('l.' + c.strip() for c in self._COLS.split(','))} "
               "FROM rev r JOIN lemma l ON l.id = r.lemma_id WHERE r.key=?")
        args: list = [fold(form)]
        if lang:
            sql += " AND l.lang=?"
            args.append(lang)
        return [self._verb(r) for r in self.con.execute(sql + " ORDER BY l.score DESC", args)]

    def by_gloss(self, head: str, lang: str, limit: int = 5) -> list[Verb]:
        """Verbs of `lang` glossed with English `head`, best match first."""
        rows = self.con.execute(
            f"SELECT {', '.join('l.' + c.strip() for c in self._COLS.split(','))} "
            "FROM gloss g JOIN lemma l ON l.id = g.lemma_id "
            "WHERE g.head=? AND l.lang=? ORDER BY g.rank > 2, l.score DESC LIMIT ?",
            (fold(head), lang, limit),
        )
        return [self._verb(r) for r in rows]

    @lru_cache(maxsize=4)
    def lemma_index(self, lang: str | None = None) -> list[tuple[str, str, str, int, int]]:
        """(folded key, lemma, lang, score, id) for fuzzy search."""
        sql = "SELECT key, lemma, lang, score, id FROM lemma"
        rows = self.con.execute(sql + (" WHERE lang=?" if lang else ""), (lang,) if lang else ())
        return list(rows)

    def meta(self) -> dict[str, str]:
        return dict(self.con.execute("SELECT k, v FROM meta"))
