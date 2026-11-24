"""Build the conjugation database from Wiktextract (kaikki.org) verb dumps.

Usage:  uv run python -m conj.build [--src DIR] [--refresh]

Data: Wiktionary contributors, extracted by Wiktextract (Ylonen 2022),
CC BY-SA 4.0. See DATA_LICENSE.md.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
import re
import shutil
import sqlite3
import sys
import urllib.request
import zlib
from collections.abc import Iterator
from pathlib import Path

from .langs.base import (
    FINITE, IMP, IND_PRS, IND_PST, INF, NONFINITE, PERSONS, PTCP_PRS, PTCP_PST, SBJV_IPFV,
    SBJV_PRS,
)
from .normalize import fold, it_orthography
from .tags import cells

KAIKKI = "https://kaikki.org/dictionary/{name}/pos-verb/kaikki.org-dictionary-{name}-by-pos-verb.jsonl"
SOURCES = {"fr": "French", "it": "Italian", "en": "English", "es": "Spanish", "pt": "Portuguese"}
OUT = Path(__file__).parent / "data" / "conj.sqlite.gz"

Paradigm = dict[str, dict[str, list[str]] | list[str]]


# ---------------------------------------------------------------- download
def download(lang: str, src: Path, refresh: bool) -> Path:
    name = SOURCES[lang]
    path = src / f"{name}.jsonl"
    if path.exists() and not refresh:
        return path
    src.mkdir(parents=True, exist_ok=True)
    url = KAIKKI.format(name=name)
    print(f"downloading {url}", file=sys.stderr)
    # kaikki serves the dumps gzip-encoded on request: ~10x smaller to download.
    req = urllib.request.Request(url, headers={"User-Agent": "conj-build/0.1", "Accept-Encoding": "gzip"})
    tmp = path.with_suffix(".part")
    with urllib.request.urlopen(req) as resp, open(tmp, "wb") as fh:
        body = gzip.GzipFile(fileobj=resp) if resp.headers.get("Content-Encoding") == "gzip" else resp
        shutil.copyfileobj(body, fh, length=1 << 20)
    tmp.rename(path)
    return path


def entries(path: Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line)
            if entry.get("pos") == "verb":
                yield entry


# ---------------------------------------------------------------- glosses
_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]|\{[^}]*\}")
# Senses that are not a current, general meaning of the verb. Dropped unless
# nothing else is left (estudar: "alternative form of estuprar", an Internet euphemism).
SENSE_NOISE = frozenset({
    "alt-of", "obsolete", "archaic", "dialectal", "rare", "Internet", "misspelling",
})


def glosses(entry: dict, want: str | None = None) -> list[str]:
    """Sense glosses, skipping inflected-form senses. `want` filters by sense tag."""
    main, fallback = [], []
    for sense in entry.get("senses", []):
        tags = sense.get("tags", [])
        if "form-of" in tags or sense.get("form_of"):
            continue
        if want and want not in tags:
            continue
        g = sense.get("glosses")
        if not g:
            continue
        noisy = sense.get("alt_of") or SENSE_NOISE.intersection(tags)
        bucket = fallback if noisy else main
        if g[-1] not in bucket:
            bucket.append(g[-1])
    return main or fallback


# ---------------------------------------------------------------- paradigms
def add(par: Paradigm, key: str, persons: tuple[str, ...], form: str) -> None:
    if key in NONFINITE:
        bucket = par.setdefault(key, [])
        if form not in bucket:
            bucket.append(form)
        return
    table = par.setdefault(key, {})
    for p in persons:
        bucket = table.setdefault(p, [])
        if form not in bucket:
            bucket.append(form)


def merge(into: Paradigm, other: Paradigm) -> None:
    """Fill cells of `into` that are missing, from `other`."""
    for key, val in other.items():
        if key not in into:
            into[key] = val
        elif isinstance(val, dict):
            for p, forms in val.items():
                into[key].setdefault(p, forms)


def _clean(form: str, lang: str) -> str | None:
    form = form.strip()
    if not form or form in {"-", "—", "–"} or form.startswith("'"):
        return None
    if any("\u0250" <= ch <= "\u02af" for ch in form):  # IPA leaked into a cell (paʁl)
        return None
    return it_orthography(form) if lang == "it" else form


def _aux_fr(text: str) -> list[str]:
    """'avoir + past participle' -> ['avoir']; 'avoir or être + ...' -> both, in order."""
    head = text.split(" + ")[0]
    found = [(m.start(), m.group()) for m in re.finditer(r"\b(avoir|être)\b", head)]
    return [aux for _, aux in sorted(found)]


# Être-verbs that take avoir when transitive (il est monté / il a monté l'escalier).
FR_DUAL_AUX = {
    "monter", "descendre", "sortir", "rentrer", "retourner", "passer", "remonter",
    "redescendre", "ressortir", "repasser", "demeurer", "accourir", "apparaître",
}


# Spanish and Portuguese form every compound tense with one auxiliary.
ROMANCE_AUX = {"es": "haber", "pt": "ter"}


def romance_records(entry: dict, lang: str) -> list[dict]:
    """One record per paradigm in the entry.

    An entry can hold several conjugation tables: French adds pronominal ones
    (se laver, s'en aller), Italian adds variant ones for the same verb. Each
    table is keyed by its own infinitive; tables sharing an infinitive merge.
    """
    rows = [f for f in entry.get("forms", []) if f.get("source") == "conjugation"]
    if not rows:
        return []
    tables: list[dict] = []
    for row in rows:
        tags = row.get("tags", [])
        if "table-tags" in tags or not tables:
            tables.append({"par": {}, "aux": [], "lemma": None, "refl": False})
        rec = tables[-1]
        rec["refl"] |= "reflexive" in tags
        form = row.get("form", "")
        if "auxiliary" in tags and lang == "it":
            aux = fold(form)
            if aux not in rec["aux"]:
                rec["aux"].append(aux)
            continue
        if lang == "fr" and "infinitive" in tags and "multiword-construction" in tags:
            rec["aux"] = _aux_fr(form)
            continue
        cell = cells(tags, lang)
        if cell is None:
            continue
        form = _clean(form, lang)
        if form is None:
            continue
        if cell[0] == INF and rec["lemma"] is None:
            rec["lemma"] = form
        add(rec["par"], *cell, form)

    word = entry["word"]
    merged: dict[str, dict] = {}
    for rec in tables:
        if not rec["par"]:
            continue
        lemma = rec["lemma"] or word
        pronominal = lemma != word and (rec["refl"] or lemma.startswith(("se ", "s'")) or lang == "it")
        if lemma != word and not pronominal:
            lemma = word  # spelling variant of the same infinitive
        have = merged.get(lemma)
        if have:
            merge(have["par"], rec["par"])
            have["aux"] += [a for a in rec["aux"] if a not in have["aux"]]
            continue
        if lemma == word:
            gl = glosses(entry)
        else:
            gl = glosses(entry, "reflexive") or glosses(entry, "pronominal") or glosses(entry)
        merged[lemma] = {"lemma": lemma, "par": rec["par"], "aux": list(rec["aux"]),
                         "glosses": gl, "table": True}

    for lemma, rec in merged.items():
        aux = [a for a in rec["aux"] if a in ("avoir", "être", "avere", "essere")]
        if lang == "fr":
            if lemma != word or lemma.startswith(("se ", "s'")):
                aux = ["être"]
            elif lemma in FR_DUAL_AUX:
                aux = (aux or ["être"]) + [a for a in ("être", "avoir") if a not in aux]
            aux = aux or ["avoir"]
        elif lang in ROMANCE_AUX:  # one auxiliary for every verb: haber, ter
            aux = [ROMANCE_AUX[lang]]
        elif not aux and not rec["aux"]:
            aux = ["avere"]  # no auxiliary row at all; "-" means no compound tenses
        rec["aux"] = aux
    return list(merged.values())


def _en_parts(entry: dict) -> dict[str, list[str]]:
    parts: dict[str, list[str]] = {"s3": [], "ing": [], "past": [], "pp": []}
    for f in entry.get("forms", []):
        if f.get("source"):
            continue
        tags = frozenset(f.get("tags", []))
        if tags & {"archaic", "obsolete", "nonstandard", "dialectal", "rare", "alternative"}:
            continue
        form = f.get("form", "").strip()
        if not form or form.startswith("'") or form == "-":
            continue
        if tags == {"present", "singular", "third-person"}:
            slot = "s3"
        elif tags == {"participle", "present"}:
            slot = "ing"
        elif tags == {"participle", "past"}:
            slot = "pp"
        elif tags == {"past"}:
            slot = "past"
        else:
            continue
        if form not in parts[slot]:
            parts[slot].append(form)
    return parts


def english_record(entry: dict) -> dict | None:
    gl = glosses(entry)
    if not gl:
        return None  # only inflected-form senses ("walked: simple past of walk")
    word = entry["word"]
    par: Paradigm = {}
    parts = _en_parts(entry)
    if parts["s3"] and parts["past"]:
        base = [word]
        pp = parts["pp"] or parts["past"]
        ing = parts["ing"] or [word + "ing"]
        par[IND_PRS] = {p: list(base) for p in PERSONS}
        par[IND_PRS]["3s"] = parts["s3"]
        par[IND_PST] = {p: list(parts["past"]) for p in PERSONS}
        par[SBJV_PRS] = {p: list(base) for p in PERSONS}
        par[SBJV_IPFV] = {p: list(parts["past"]) for p in PERSONS}
        par[INF], par[PTCP_PRS], par[PTCP_PST] = base, ing, pp

    table: Paradigm = {}
    for row in entry.get("forms", []):
        if row.get("source") != "conjugation":
            continue
        cell = cells(row.get("tags", []))
        form = _clean(row.get("form", ""), "en")
        if cell and form:
            add(table, *cell, form)
    if table:
        # Modern English "you" shares the plural forms (are/were, not art/wast).
        for key in (IND_PRS, IND_PST):
            if key in table and "2p" in table[key]:
                table[key]["2s"] = list(table[key]["2p"])
        for key, val in table.items():
            par[key] = val
    if not par:
        return None
    base = (par.get(INF) or [word])[0]
    par[IMP] = {"2s": [base], "1p": [f"let's {base}"], "2p": [base]}
    return {"lemma": word, "par": par, "aux": [], "glosses": gl, "table": bool(table)}


# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE lemma(
    id INTEGER PRIMARY KEY, lang TEXT NOT NULL, lemma TEXT NOT NULL, key TEXT NOT NULL,
    score INTEGER NOT NULL, aux TEXT NOT NULL, glosses TEXT NOT NULL,
    paradigm BLOB NOT NULL
);
CREATE TABLE rev(key TEXT NOT NULL, lemma_id INTEGER NOT NULL, PRIMARY KEY (key, lemma_id)) WITHOUT ROWID;
"""
INDEXES = """
CREATE INDEX lemma_key ON lemma(lang, key);
"""


# Closed class: no infinitive, participles, imperative or periphrastic tenses.
EN_MODALS = {"can", "could", "may", "might", "must", "shall", "should", "will", "would", "ought"}


def finalize(lang: str, rec: dict) -> None:
    par = rec["par"]
    if lang == "it":
        # Italian tables list regional/literary variants (damo, demo) after the
        # standard form, often without any tag: keep the standard one.
        for key, val in par.items():
            if isinstance(val, list):
                par[key] = val[:1]
            else:
                for p in val:
                    val[p] = val[p][:1]
    if lang == "en" and rec["lemma"] in EN_MODALS:
        rec["par"] = {k: v for k, v in par.items() if k in (IND_PRS, IND_PST)}
        for table in rec["par"].values():
            for p in PERSONS:  # modals do not inflect for person
                table[p] = list(table.get("1s") or table.get(p) or [])


def collect(lang: str, path: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for entry in entries(path):
        recs = english_record(entry) if lang == "en" else romance_records(entry, lang)
        for rec in [recs] if isinstance(recs, dict) else recs or []:
            have = records.get(rec["lemma"])
            if have is None:
                records[rec["lemma"]] = rec
                continue
            merge(have["par"], rec["par"])
            have["glosses"] += [g for g in rec["glosses"] if g not in have["glosses"]]
            have["aux"] += [a for a in rec["aux"] if a not in have["aux"]]
            have["table"] |= rec["table"]
    for rec in records.values():
        finalize(lang, rec)
    return records


def coverage(lang: str, records: dict[str, dict]) -> None:
    core = (IND_PRS, PTCP_PST) if lang != "en" else (IND_PRS, IND_PST, PTCP_PST)
    missing = [l for l, r in records.items() if any(k not in r["par"] for k in core)
               and l not in EN_MODALS]
    print(f"{lang}: {len(records):>6} lemmas, {len(missing)} missing core cells "
          f"(e.g. {', '.join(sorted(missing)[:8])})", file=sys.stderr)


PRONOMINAL_ENDINGS = {"it": ("rsi", "rsene"), "es": ("rse",), "pt": ("-se",)}


def frequency(lang: str, rec: dict) -> int:
    """Corpus frequency of the verb: summed over its distinct forms, as Zipf x 100.

    Wiktionary has no frequency data; wordfreq (CC BY-SA 4.0 data) is used at
    build time only, to rank search results and translation candidates.
    """
    from wordfreq import word_frequency

    forms: set[str] = set()
    for val in rec["par"].values():
        for fs in [val] if isinstance(val, list) else val.values():
            # the verb itself: "me lève" -> "lève", but "parks in" -> "parks"
            forms.update(f.split(" ")[0 if lang == "en" else -1] for f in fs)
    if lang == "en":  # "walk" is also a noun: count only the inflected forms too
        forms.add(rec["lemma"])
    total = sum(word_frequency(f, lang) for f in forms)
    score = round(100 * (math.log10(total) + 9)) if total > 0 else 0
    # Pronominals were scored on their base verb's forms (si vuole -> vuole): rank them below it.
    # Same for English phrasal verbs (find out -> find).
    if " " in rec["lemma"] or rec["lemma"].endswith(PRONOMINAL_ENDINGS.get(lang, ())):
        score -= 100
    return max(score, 0)


def write(db_path: Path, data: dict[str, dict[str, dict]]) -> None:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    lid = 0
    for lang, records in data.items():
        for rec in records.values():
            lid += 1
            score = frequency(lang, rec)
            blob = zlib.compress(json.dumps(rec["par"], ensure_ascii=False).encode(), 9)
            con.execute(
                "INSERT INTO lemma VALUES (?,?,?,?,?,?,?,?)",
                (lid, lang, rec["lemma"], fold(rec["lemma"]), score,
                 json.dumps(rec["aux"], ensure_ascii=False),
                 json.dumps(rec["glosses"][:8], ensure_ascii=False), blob),
            )
            keys = set()
            for val in rec["par"].values():
                for forms in [val] if isinstance(val, list) else val.values():
                    keys.update(fold(f) for f in forms)
            con.executemany("INSERT INTO rev VALUES (?,?)", [(k, lid) for k in keys])
    con.executemany("INSERT INTO meta VALUES (?,?)", [
        ("built", dt.date.today().isoformat()),
        ("source", "Wiktionary via Wiktextract/kaikki.org"),
        ("license", "CC BY-SA 4.0"),
    ])
    con.executescript(INDEXES)
    con.commit()
    con.execute("VACUUM")
    con.close()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=Path.home() / ".cache" / "conj-build",
                    help="where the kaikki dumps are downloaded (default: %(default)s)")
    ap.add_argument("--refresh", action="store_true", help="re-download the dumps")
    ap.add_argument("--out", type=Path, default=OUT, help="output .sqlite.gz (default: %(default)s)")
    ap.add_argument("--langs", default=",".join(SOURCES), help="comma-separated (default: %(default)s)")
    args = ap.parse_args(argv)

    data = {}
    for lang in args.langs.split(","):
        data[lang] = collect(lang, download(lang, args.src, args.refresh))
        coverage(lang, data[lang])

    raw = args.out.with_suffix("")  # .sqlite
    raw.parent.mkdir(parents=True, exist_ok=True)
    write(raw, data)
    with open(raw, "rb") as src, gzip.open(args.out, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB; "
          f"uncompressed {raw.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)
    sha = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"sha256 {sha}\n(to publish: new GitHub release, then set DATA_TAG and DATA_SHA256 in db.py)",
          file=sys.stderr)
    raw.unlink()


if __name__ == "__main__":
    main()
