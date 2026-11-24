"""Generate French pronominal paradigms (se lever) from the base verb (lever).

Wiktionary ships an explicit pronominal table for only a few hundred French
verbs; for the rest, the pronominal forms follow mechanically from the base.
"""

from __future__ import annotations

import re

from .db import Verb
from .langs.base import FINITE, IMP, INF, PTCP_PRS
from .normalize import fr_elides

CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nous", "2p": "vous", "3p": "se"}
IMP_CLITIC = {"2s": "toi", "1p": "nous", "2p": "vous"}
PRONOMINAL = re.compile(r"^(?:se\s+|s['’])(\S.*)$", re.IGNORECASE)


def with_clitic(clitic: str, form: str, lemma: str) -> str:
    if clitic in ("me", "te", "se") and fr_elides(form, lemma):
        return f"{clitic[0]}'{form}"
    return f"{clitic} {form}"


def pronominal_lemma(base: str) -> str:
    return with_clitic("se", base, base)


def make_pronominal(base: Verb) -> Verb:
    par = base.paradigm
    new: dict = {}
    for tense in FINITE:
        table = par.get(tense)
        if not isinstance(table, dict):
            continue
        if tense == IMP:
            new[IMP] = {p: [f"{f}-{IMP_CLITIC[p]}" for f in fs]
                        for p, fs in table.items() if p in IMP_CLITIC}
        else:
            new[tense] = {p: [with_clitic(CLITIC[p], f, base.lemma) for f in fs]
                          for p, fs in table.items()}
    for nf, val in par.items():
        if isinstance(val, list):
            new[nf] = [with_clitic("se", f, base.lemma) for f in val] if nf in (INF, PTCP_PRS) else val
    verb = Verb(
        id=-base.id, lang="fr", lemma=pronominal_lemma(base.lemma), score=base.score,
        aux=["être"], glosses=base.glosses, _blob=b"",
    )
    verb.__dict__["paradigm"] = new  # pre-fill the cached_property
    verb.generated = True
    return verb
