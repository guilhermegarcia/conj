"""Find verbs from what the user types: lemma prefix, fuzzy lemma, or inflected form."""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz, process

from .db import DB, Verb
from .normalize import fold
from .pronominal import PRONOMINAL, make_pronominal, pronominal_lemma


@dataclass(frozen=True)
class Hit:
    id: int
    lang: str
    lemma: str
    via: str  # "lemma", "form" or "fuzzy"
    form: str | None = None  # the inflected form typed, for via == "form"


def resolve(db: DB, hit: Hit) -> Verb:
    """The Verb behind a search hit (negative ids are generated pronominals)."""
    return make_pronominal(db.by_id(-hit.id)) if hit.id < 0 else db.by_id(hit.id)


def parse_query(text: str) -> tuple[str | None, str]:
    """'it:venire' -> ('it', 'venire')."""
    if len(text) > 3 and text[2] == ":" and text[:2].lower() in ("fr", "it", "en"):
        return text[:2].lower(), text[3:].strip()
    return None, text.strip()


def search(db: DB, text: str, lang: str | None = None, limit: int = 30) -> list[Hit]:
    qlang, query = parse_query(text)
    lang = qlang or lang
    key = fold(query)
    if not key:
        return []
    index = db.lemma_index(lang)
    hits: list[Hit] = []
    seen: set[int] = set()

    def push(hit: Hit) -> None:
        if hit.id not in seen and len(hits) < limit:
            seen.add(hit.id)
            hits.append(hit)

    # 0. French pronominals ("se lev..."): stored ones, else generated from the base verb
    m = PRONOMINAL.match(key)
    if m and lang in (None, "fr"):
        stored = {r[0]: r for r in db.lemma_index("fr")}
        bases = [r for r in db.lemma_index("fr") if r[0].startswith(m.group(1))
                 and not PRONOMINAL.match(r[0])]
        bases.sort(key=lambda r: (r[0] != m.group(1), -r[3]))
        for k, lemma, lg, score, id_ in bases[:8]:
            have = stored.get(fold(pronominal_lemma(lemma)))
            if have:
                push(Hit(have[4], "fr", have[1], "lemma"))
            else:
                push(Hit(-id_, "fr", pronominal_lemma(lemma), "pronominal"))

    # 1. exact lemma
    exact = [r for r in index if r[0] == key]
    for k, lemma, lg, score, id_ in sorted(exact, key=lambda r: -r[3]):
        push(Hit(id_, lg, lemma, "lemma"))
    # 2. inflected forms ("vengo" -> venire)
    for verb in db.reverse(query, lang)[:10]:
        push(Hit(verb.id, verb.lang, verb.lemma, "form", query))
    # 3. lemmas starting with the query, most frequent first
    prefix = [r for r in index if r[0].startswith(key) and r[0] != key]
    prefix.sort(key=lambda r: -r[3])
    for k, lemma, lg, score, id_ in prefix[:12]:
        push(Hit(id_, lg, lemma, "lemma"))
    # 4. fuzzy (typos)
    if len(hits) < limit and len(key) >= 3:
        keys = [r[0] for r in index]
        for _, sim, i in process.extract(key, keys, scorer=fuzz.ratio, limit=limit, score_cutoff=70):
            k, lemma, lg, score, id_ = index[i]
            push(Hit(id_, lg, lemma, "fuzzy"))
    return hits
