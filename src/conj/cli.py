"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from . import AUTHOR, NAME, __version__
from .compound import conjugate
from .db import DB
from .langs import LANGS
from .normalize import fold
from .render import as_dict, describe, plain
from .search import resolve, search


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        prog="conj",
        description=f"{NAME}: verb conjugation for French, Italian, Spanish, Portuguese, "
                    "English and German. Without --plain, opens the interactive TUI.",
        epilog="Examples: conj · conj venir · conj it andare · conj --plain fr aller · conj -p went",
    )
    ap.add_argument("words", nargs="*", metavar="[LANG] VERB",
                    help="verb or inflected form, optionally preceded by fr/it/es/pt/en/de")
    ap.add_argument("-V", "--version", action="version",
                    version=f"{NAME} {__version__} (conj) by {AUTHOR}")
    ap.add_argument("-p", "--plain", action="store_true", help="print the table instead of opening the TUI")
    ap.add_argument("-s", "--simple", action="store_true", help="simple tenses only")
    ap.add_argument("-j", "--json", action="store_true",
                    help="print the conjugation as JSON (exact matches only; for editor plugins)")
    ap.add_argument("--prefer", choices=sorted(LANGS), metavar="LANG",
                    help="with --json: list this language's verbs first (without restricting)")
    ap.add_argument("-a", "--aux", help="auxiliary for compound tenses (e.g. essere / avere)")
    args = ap.parse_args(argv)

    lang = None
    words = " ".join(args.words).split()
    if words and words[0].lower() in LANGS and len(words) > 1:
        lang = words.pop(0).lower()
    query = " ".join(words)

    try:
        db = DB()
    except FileNotFoundError as e:
        sys.exit(str(e))

    if args.json:
        print_json(db, query, lang, args.aux, compounds=not args.simple, prefer=args.prefer)
        return

    if not args.plain:
        from .tui.app import ConjApp
        ConjApp(db, query=query, lang=lang).run()
        return

    if not query:
        ap.error("--plain needs a verb")
    hits = search(db, query, lang, limit=8)
    if not hits:
        sys.exit(f"no verb found for {query!r}")
    hit = hits[0]
    verb = resolve(db, hit)
    conj = conjugate(db, verb, args.aux)
    if hit.via == "form":
        where = describe(conj, conj.find(query))  # empty for search-only forms (de: aufstehe)
        print(f"{query} → {verb.lemma}" + (f" ({where})" if where else "") + "\n")
    elif hit.via == "fuzzy":
        print(f"(no exact match for {query!r}; showing {verb.lemma})\n")
    sys.stdout.write(plain(conj, compounds=not args.simple))
    others = [f"{h.lemma} ({h.lang})" for h in hits[1:6] if h.via != "fuzzy"]
    if others:
        print(f"\nalso: {', '.join(others)}")


def print_json(db: DB, query: str, lang: str | None, aux: str | None, compounds: bool,
               prefer: str | None = None, max_candidates: int = 6) -> None:
    """Exact matches only: an inflected form or a lemma, never a prefix or a typo.

    The top level is the best match; `candidates` holds every match (best first), each
    with its own full conjugation, so an editor can switch between them without
    running conj again. `prefer` moves that language's matches to the front (a guess,
    e.g. the editor's spell-check language), unlike `lang`, which restricts.
    """
    key = fold(query)
    hits = search(db, query, lang, limit=16) if key else []
    exact = [h for h in hits if h.via in ("form", "pronominal") or fold(h.lemma) == key]
    if prefer:
        exact.sort(key=lambda h: h.lang != prefer)  # stable: rank kept within each group
    if not exact:
        out = {"found": False, "query": query}
    else:
        candidates = []
        for hit in exact[:max_candidates]:
            conj = conjugate(db, resolve(db, hit), aux)
            candidates.append({"query": query, **as_dict(conj, conj.find(query), compounds)})
        out = {**candidates[0], "candidates": candidates,
               "also": [f"{c['lemma']} ({c['lang']})" for c in candidates[1:]]}
    json.dump(out, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
