"""Generate pronominal paradigms from the base verb when Wiktionary has no table.

French se lever from lever, Spanish levantarse from levantar, Portuguese
levantar-se from levantar. Wiktionary ships explicit pronominal tables for only
a few hundred verbs; for the rest, the forms follow mechanically from the base.

Portuguese uses Brazilian placement: proclisis in finite tenses (eu me levanto,
eu tenho me levantado), enclisis in the affirmative imperative (levante-se)
and in the citation forms (levantar-se, levantando-se).
"""

from __future__ import annotations

import re
import unicodedata

from .db import Verb
from .langs.base import FINITE, GER, IMP, INF, PTCP_PRS
from .normalize import fr_elides

CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nous", "2p": "vous", "3p": "se"}
IMP_CLITIC = {"2s": "toi", "1p": "nous", "2p": "vous"}
PRONOMINAL = re.compile(r"^(?:se\s+|s['’])(\S.*)$", re.IGNORECASE)

ES_CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nos", "2p": "os", "3p": "se"}
PT_CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nos", "2p": "vos", "3p": "se"}
# Folded search keys of a pronominal infinitive -> the base verb's key.
ES_PRONOMINAL = re.compile(r"^(\S*[aei]r)se$")
PT_PRONOMINAL = re.compile(r"^(\S*[aeio]r)(?:-| )se$")


def with_clitic(clitic: str, form: str, lemma: str) -> str:
    if clitic in ("me", "te", "se") and fr_elides(form, lemma):
        return f"{clitic[0]}'{form}"
    return f"{clitic} {form}"


def pronominal_lemma(base: str, lang: str = "fr") -> str:
    if lang == "es":
        return es_enclitic(base, "se")
    if lang == "pt":
        return f"{base}-se"
    return with_clitic("se", base, base)


# ------------------------------------------------------------------ Spanish stress
_ACUTE = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú"}
_ACCENTED = set(_ACUTE.values())
_STRONG = set("aeo") | _ACCENTED


def _nuclei(word: str) -> list[list[int]]:
    """Syllable nuclei as lists of vowel indexes (diphthongs share a nucleus)."""
    out: list[list[int]] = []
    prev_vowel = False
    for i, ch in enumerate(word):
        silent_u = ch == "u" and i and word[i - 1] in "qg" and word[i + 1: i + 2] in ("e", "i")
        if ch not in "aeiouáéíóúü" or silent_u:
            prev_vowel = False
            continue
        if prev_vowel and not (ch in _STRONG and word[out[-1][-1]] in _STRONG):
            out[-1].append(i)  # diphthong: at most one strong vowel
        else:
            out.append([i])  # new syllable (or hiatus between two strong vowels)
        prev_vowel = True
    return out


def _stress(word: str) -> int:
    """Index of the stressed vowel, by the written accent or the default rule."""
    for i, ch in enumerate(word):
        if ch in _ACCENTED:
            return i
    nuclei = _nuclei(word)
    if not nuclei:
        return 0
    nucleus = nuclei[-2] if len(nuclei) > 1 and word[-1] in "aeiouns" else nuclei[-1]
    strong = [i for i in nucleus if word[i] in _STRONG]
    return strong[0] if strong else nucleus[-1]


def es_enclitic(form: str, clitic: str, drop: int = 0) -> str:
    """Attach `clitic` after `form`, keeping its stress: levanta + te -> levántate."""
    form = unicodedata.normalize("NFC", form)
    stress = _stress(form)
    new = form[: len(form) - drop] + clitic
    if any(ch in _ACCENTED for ch in new) or _stress(new) == stress:
        return new
    return new[:stress] + _ACUTE[new[stress]] + new[stress + 1:]


# ------------------------------------------------------------------ builders
def _fr(par: dict, lemma: str) -> dict:
    new: dict = {}
    for tense in FINITE:
        table = par.get(tense)
        if not isinstance(table, dict):
            continue
        if tense == IMP:
            new[IMP] = {p: [f"{f}-{IMP_CLITIC[p]}" for f in fs]
                        for p, fs in table.items() if p in IMP_CLITIC}
        else:
            new[tense] = {p: [with_clitic(CLITIC[p], f, lemma) for f in fs]
                          for p, fs in table.items()}
    for nf, val in par.items():
        if isinstance(val, list):
            new[nf] = [with_clitic("se", f, lemma) for f in val] if nf in (INF, PTCP_PRS) else val
    return new


def _es_imperative(person: str, form: str) -> str:
    if person == "1p" and form.endswith("s"):
        return es_enclitic(form, "nos", drop=1)  # levantemos -> levantémonos
    if person == "2p":
        return "idos" if form == "id" else es_enclitic(form, "os", drop=1)  # levantad -> levantaos
    return es_enclitic(form, ES_CLITIC[person])


def _pt_imperative(person: str, form: str) -> str:
    if person == "1p" and form.endswith("s"):
        return f"{form[:-1]}-nos"  # levantemos -> levantemo-nos
    return f"{form}-{PT_CLITIC[person]}"


def _iberian(par: dict, lang: str) -> dict:
    clitics = ES_CLITIC if lang == "es" else PT_CLITIC
    imperative = _es_imperative if lang == "es" else _pt_imperative
    new: dict = {}
    for tense in FINITE:
        table = par.get(tense)
        if not isinstance(table, dict):
            continue
        if tense == IMP:
            new[IMP] = {p: [imperative(p, f) for f in fs] for p, fs in table.items()}
        else:  # proclisis: me levanto (Spanish, and Brazilian Portuguese)
            new[tense] = {p: [f"{clitics[p]} {f}" for f in fs] for p, fs in table.items()}
    for nf, val in par.items():
        if isinstance(val, list):
            if nf in (INF, GER):
                new[nf] = [es_enclitic(f, "se") if lang == "es" else f"{f}-se" for f in val]
            else:
                new[nf] = val
    return new


def make_pronominal(base: Verb) -> Verb:
    if base.lang == "fr":
        par, aux = _fr(base.paradigm, base.lemma), ["être"]
    else:
        par, aux = _iberian(base.paradigm, base.lang), list(base.aux)
    verb = Verb(
        id=-base.id, lang=base.lang, lemma=pronominal_lemma(base.lemma, base.lang),
        score=base.score, aux=aux, glosses=base.glosses, _blob=b"",
    )
    verb.__dict__["paradigm"] = par  # pre-fill the cached_property
    verb.generated = True
    verb.base_lemma = base.lemma
    return verb
