"""Read-only access to the conjugation database."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import urllib.request
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
    """Path of the uncompressed database.

    In order: $CONJ_DB; the packaged copy (built with conj-build or downloaded
    by hand); else the release this version of the code was made for, which is
    downloaded once into the cache.
    """
    if env := os.environ.get("CONJ_DB"):
        return Path(env)
    if PACKAGED.exists():
        stamp = PACKAGED.stat()
        target = cache_dir() / f"conj-{stamp.st_size}-{int(stamp.st_mtime)}.sqlite"
        if not target.exists():
            _unpack(PACKAGED, target)
        return target
    target = cache_dir() / f"conj-{DATA_TAG}.sqlite"
    if not target.exists():
        url = os.environ.get("CONJ_DB_URL", DATA_URL)
        gz = target.with_suffix(".sqlite.gz.part")
        try:
            download(url, gz, DATA_SHA256)
        except (OSError, ValueError) as e:
            gz.unlink(missing_ok=True)
            raise FileNotFoundError(
                f"Could not download the verb database ({e}).\n"
                f"  Download it by hand: {url}\n"
                f"  and save it as {PACKAGED},\n"
                f"  or build it from Wiktionary with: uv run conj-build"
            ) from e
        _unpack(gz, target)
        gz.unlink()
    return target


# The database release this version of the code reads. After `conj-build` and a
# new GitHub release, update both values (conj-build prints the checksum).
DATA_TAG = "data-2026-11-23c"
DATA_SHA256 = "b80f41706b1b5e8fcb08bef29f1f927e686f1637ad84a83109bdc2178732848e"
DATA_URL = f"https://github.com/guilhermegarcia/conj/releases/download/{DATA_TAG}/conj.sqlite.gz"


def download(url: str, dest: Path, sha256: str | None) -> None:
    """Fetch `url` into `dest`, showing progress on stderr; check the SHA-256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "conj"})
    print("conj: first run, downloading the verb database…", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=30) as resp, open(dest, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while chunk := resp.read(1 << 16):
            fh.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if total and sys.stderr.isatty():
                print(f"\r  {done / 1e6:5.1f} / {total / 1e6:.1f} MB", end="", file=sys.stderr)
    if total and sys.stderr.isatty():
        print(file=sys.stderr)
    if sha256 and digest.hexdigest() != sha256:
        raise ValueError(f"checksum mismatch: got {digest.hexdigest()[:12]}…, expected {sha256[:12]}…")


def _unpack(gz: Path, target: Path) -> None:
    """Decompress `gz` to `target`, removing older unpacked databases."""
    target.parent.mkdir(parents=True, exist_ok=True)
    for old in target.parent.glob("conj-*.sqlite"):
        old.unlink()
    tmp = target.with_suffix(".part")
    with gzip.open(gz, "rb") as src, open(tmp, "wb") as dst:
        shutil.copyfileobj(src, dst)
    tmp.rename(target)


@dataclass
class Verb:
    id: int
    lang: str
    lemma: str
    score: int
    aux: list[str]
    glosses: list[str]
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

    _COLS = "id, lang, lemma, score, aux, glosses, paradigm"

    def _verb(self, row) -> Verb:
        id_, lang, lemma, score, aux, gl, blob = row
        return Verb(id_, lang, lemma, score, json.loads(aux), json.loads(gl), blob)

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

    @lru_cache(maxsize=4)
    def lemma_index(self, lang: str | None = None) -> list[tuple[str, str, str, int, int]]:
        """(folded key, lemma, lang, score, id) for fuzzy search."""
        sql = "SELECT key, lemma, lang, score, id FROM lemma"
        rows = self.con.execute(sql + (" WHERE lang=?" if lang else ""), (lang,) if lang else ())
        return list(rows)

    def meta(self) -> dict[str, str]:
        return dict(self.con.execute("SELECT k, v FROM meta"))
