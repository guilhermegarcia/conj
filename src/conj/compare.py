"""Cross-language equivalents through English glosses."""

from __future__ import annotations

from .db import DB, Verb


def equivalents(db: DB, verb: Verb, langs: tuple[str, ...] = ("fr", "it", "en"),
                limit: int = 5) -> dict[str, list[Verb]]:
    """For each language, verbs that translate `verb` (the verb itself for its own language).

    French and Italian verbs carry English glosses ("to run, hurry"); their head
    verbs index both directions, so courir -> run -> correre.
    """
    heads = verb.heads or []
    out: dict[str, list[Verb]] = {}
    for lang in langs:
        if lang == verb.lang:
            out[lang] = [verb]
            continue
        found: list[Verb] = []
        for head in heads[:3]:
            if lang == "en":
                cand = [v for v in [db.get("en", head)] if v]
            else:
                cand = db.by_gloss(head, lang, limit)
            for v in cand:
                if all(v.id != f.id for f in found):
                    found.append(v)
            if len(found) >= limit:
                break
        out[lang] = found[:limit]
    return out
