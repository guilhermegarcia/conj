"""Assemble a full conjugation: stored simple tenses + built compound tenses.

Compound tenses are not stored; they are composed from the auxiliary's own
paradigm (looked up in the database) and the verb's past participle.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .db import DB, Verb
from .langs import LANGS, LangSpec
from .langs import en as EN
from .langs.base import (
    COND_PRS, FINITE, GER, IMP, IMP_NEG, IND_FUT, IND_IPFV, IND_PRS, IND_PST, INF, INF_PERS,
    NONFINITE, PERSONS, PTCP_PRS, PTCP_PST, SBJV_FUT, SBJV_IPFV, SBJV_PRS, compound,
)
from .normalize import fold, fr_elides

ROMANCE_AUX_TENSES = (IND_PRS, IND_IPFV, IND_PST, IND_FUT, COND_PRS, SBJV_PRS, SBJV_IPFV, SBJV_FUT,
                      INF_PERS)
NEGATION = {"es": "no", "pt": "não"}
# Imperative persons that need a pronoun to be read right: usted, você.
IMP_SUBJECT = {
    "it": {"3s": "(Lei) ", "3p": "(Loro) "},
    "es": {"3s": "(usted) ", "3p": "(ustedes) "},
    "pt": {"3s": "(você) ", "3p": "(vocês) "},
}
BE_AUX = {"être", "essere"}


@dataclass
class Cell:
    person: str | None  # None for non-finite forms
    pron: str  # subject part, including trailing space or apostrophe ("j'")
    form: str


@dataclass
class Conjugation:
    verb: Verb
    spec: LangSpec
    aux: str | None
    aux_options: list[str]
    tables: dict[str, list[Cell]] = field(default_factory=dict)

    def find(self, form: str) -> list[tuple[str, str | None]]:
        """(tense key, person) of every cell whose form matches `form`.

        Exact matches win: in Spanish and Portuguese an accent tells forms apart
        (hablé / hable, falámos / falamos). Without one, match accent-insensitively.
        """
        exact = unicodedata.normalize("NFC", form.strip().lower())
        key = fold(form)
        hits: dict[bool, list[tuple[str, str | None]]] = {True: [], False: []}
        for tense, cells in self.tables.items():
            for c in cells:
                variants = c.form.split(" / ")
                if any(unicodedata.normalize("NFC", v.lower()) == exact for v in variants):
                    hits[True].append((tense, c.person))
                elif any(fold(v) == key for v in variants):
                    hits[False].append((tense, c.person))
        return hits[True] or hits[False]


# ------------------------------------------------------------------ helpers
def first(par: dict, tense: str, person: str | None = None) -> str | None:
    val = par.get(tense)
    if not val:
        return None
    if person is None:
        return val[0] if isinstance(val, list) else None
    forms = val.get(person) if isinstance(val, dict) else None
    return forms[0] if forms else None


def reflexive(verb: Verb) -> str | None:
    """Clitic class of a pronominal verb: 'se', 'sene' (s'en aller, andarsene), or None."""
    lemma = verb.lemma
    if verb.lang == "fr" and (lemma.startswith("s'en ") or lemma.startswith("se en ")):
        return "sene"
    if verb.lang == "fr" and (lemma.startswith("se ") or lemma.startswith("s'")):
        return "se"
    if verb.lang == "es" and lemma.endswith("rse"):
        return "se"
    if verb.lang == "pt" and lemma.endswith("-se"):
        return "se"
    if verb.lang == "it":
        if lemma.endswith("rsene"):
            return "sene"
        if lemma.endswith("rsi"):
            return "se"
    return None


FR_CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nous", "2p": "vous", "3p": "se"}
FR_CLITIC_EN = {"1s": "m'en", "2s": "t'en", "3s": "s'en", "1p": "nous en", "2p": "vous en", "3p": "s'en"}
IT_CLITIC = {"1s": "mi", "2s": "ti", "3s": "si", "1p": "ci", "2p": "vi", "3p": "si"}
ES_CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nos", "2p": "os", "3p": "se"}
PT_CLITIC = {"1s": "me", "2s": "te", "3s": "se", "1p": "nos", "2p": "vos", "3p": "se"}
IT_CLITIC_NE = {"1s": "me ne", "2s": "te ne", "3s": "se ne", "1p": "ce ne", "2p": "ve ne", "3p": "se ne"}


def fr_clitic(clitic: str, word: str) -> str:
    if clitic in ("me", "te", "se") and fr_elides(word):
        return clitic[0] + "'" + word
    return f"{clitic} {word}"


def agree_fr(pp: str, person: str | None) -> str:
    """Participle with gender/number marks, for être-compounds."""
    ends_s = pp.endswith(("s", "x"))
    if person is None:
        return pp + ("(e)" if ends_s else "(e)(s)")
    if person.endswith("s"):
        return pp + "(e)"
    if person == "2p":
        return pp + ("(e)" if ends_s else "(e)(s)")
    return pp + ("(es)" if ends_s else "(e)s")


def agree_it(pp: str, person: str | None) -> str:
    if not pp.endswith("o"):
        return pp
    stem = pp[:-1]
    if person is None:
        return f"{stem}o/a/i/e"
    return f"{stem}o/a" if person.endswith("s") else f"{stem}i/e"


def it_participle(verb: Verb) -> str | None:
    pp = first(verb.paradigm, PTCP_PST)
    if pp is None:
        return None
    kind = reflexive(verb)
    if kind == "sene" and pp.endswith("sene"):
        return pp[: -len("sene")]
    if kind == "se" and pp.endswith("si"):
        return pp[:-2]
    return pp


# ------------------------------------------------------------------ subjects
def subject(spec: LangSpec, verb: Verb, tense: str, person: str, form: str) -> str:
    """Subject (with subjunctive conjunction) to put before `form`."""
    if tense in (IMP, IMP_NEG, compound(IMP)):
        return IMP_SUBJECT.get(spec.code, {}).get(person, "")
    pron = spec.pronouns[person]
    if spec.code == "fr" and person == "1s" and fr_elides(form, verb.lemma):
        pron = "j'"
    prefix = spec.prefixes.get(tense)
    if prefix:
        if spec.code == "fr" and fr_elides(pron):
            pron = f"qu'{pron}"
        else:
            pron = f"{prefix} {pron}"
    return pron if pron.endswith("'") else pron + " "


# ------------------------------------------------------------------ builders
def simple_tables(spec: LangSpec, verb: Verb) -> dict[str, list[Cell]]:
    tables: dict[str, list[Cell]] = {}
    par = verb.paradigm
    for tense in FINITE:
        val = par.get(tense)
        if not isinstance(val, dict):
            continue
        rows = []
        for p in PERSONS:
            forms = val.get(p)
            if forms:
                rows.append(Cell(p, subject(spec, verb, tense, p, forms[0]), " / ".join(forms)))
        if rows:
            tables[tense] = rows
    if spec.code in NEGATION and IMP in tables and isinstance(par.get(SBJV_PRS), dict):
        # Negative imperative = negation + present subjunctive (no hables, não fales).
        rows = []
        for cell in tables[IMP]:
            forms = par[SBJV_PRS].get(cell.person)
            if forms:
                rows.append(Cell(cell.person, cell.pron, f"{NEGATION[spec.code]} {forms[0]}"))
        tables[IMP_NEG] = rows
    for nf in NONFINITE:
        val = par.get(nf)
        if isinstance(val, list) and val:
            text = " / ".join(val)
            if spec.code == "en" and nf == INF:
                text = "to " + text
            if spec.code == "fr" and nf == PTCP_PRS:
                tables[GER] = [Cell(None, "", "en " + val[0])]
            tables[nf] = [Cell(None, "", text)]
    return tables


def romance_compounds(db: DB, spec: LangSpec, verb: Verb, aux_lemma: str) -> dict[str, list[Cell]]:
    aux = db.get(verb.lang, aux_lemma)
    pp = it_participle(verb) if verb.lang == "it" else first(verb.paradigm, PTCP_PST)
    if aux is None or pp is None:
        return {}
    agrees = aux_lemma in BE_AUX
    kind = reflexive(verb)
    agree = agree_fr if verb.lang == "fr" else agree_it
    tables: dict[str, list[Cell]] = {}

    def participle(person: str | None) -> str:
        return agree(pp, person) if agrees else pp

    for tense in ROMANCE_AUX_TENSES:
        key = compound(tense)
        if key not in spec.labels:
            continue
        rows = []
        for p in PERSONS:
            a = first(aux.paradigm, tense, p)
            if a is None:
                continue
            if kind == "sene" and verb.lang == "fr":
                a = f"{FR_CLITIC_EN[p]} {a}"
            elif kind and verb.lang == "fr":
                a = fr_clitic(FR_CLITIC[p], a)
            elif kind and verb.lang == "es":
                a = f"{ES_CLITIC[p]} {a}"
            elif kind and verb.lang == "pt":
                pass  # the clitic goes before the participle, below
            elif kind == "sene" and a[0] in "aeèiou":  # se ne è -> se n'è
                a = f"{IT_CLITIC_NE[p][:-1]}'{a}"
            elif kind:
                a = f"{(IT_CLITIC_NE if kind == 'sene' else IT_CLITIC)[p]} {a}"
            if kind and verb.lang == "pt":  # Brazilian: eu tenho me levantado
                form = f"{a} {PT_CLITIC[p]} {participle(p)}"
            else:
                form = f"{a} {participle(p)}"
            rows.append(Cell(p, subject(spec, verb, key, p, form), form))
        if rows:
            tables[key] = rows

    # Past imperative (French only, not for pronominal verbs).
    if verb.lang == "fr" and not kind and compound(IMP) in spec.labels:
        rows = []
        for p in ("2s", "1p", "2p"):
            a = first(aux.paradigm, IMP, p)
            if a:
                rows.append(Cell(p, "", f"{a} {participle(p)}"))
        if rows:
            tables[compound(IMP)] = rows

    # Non-finite compounds: avoir parlé / ayant parlé, aver parlato / avendo parlato,
    # haber hablado / habiendo hablado, ter falado / tendo falado.
    nf_bases = {INF: first(aux.paradigm, INF)}
    nf_bases[PTCP_PRS if verb.lang == "fr" else GER] = first(
        aux.paradigm, PTCP_PRS if verb.lang == "fr" else GER)
    for nf, a in nf_bases.items():
        key = compound(nf)
        if a is None or key not in spec.labels:
            continue
        if kind == "sene" and verb.lang == "fr":
            a = f"s'en {a}"
        elif kind and verb.lang == "fr":
            a = fr_clitic("se", a)
        elif kind and verb.lang == "pt":  # ter-se, tendo-se
            a = f"{a}-se"
        elif kind and verb.lang == "es":  # haberse, habiéndose (enclitic, stress kept)
            a = (a.replace("iendo", "iéndo") if nf == GER else a) + "se"
        elif kind:  # essere -> essersi, essendo -> essendosi
            clitic = "sene" if kind == "sene" else "si"
            a = (a[:-1] if nf == INF else a) + clitic
        tables[key] = [Cell(None, "", f"{a} {participle(None)}")]
    return tables


def english_periphrastic(db: DB, spec: LangSpec, verb: Verb) -> dict[str, list[Cell]]:
    par = verb.paradigm
    base, ing, pp = first(par, INF), first(par, PTCP_PRS), first(par, PTCP_PST)
    be, have = db.get("en", "be"), db.get("en", "have")
    if not (base and ing and pp and be and have):
        return {}  # modals (can, must) have no periphrastic tenses

    def finite(aux: Verb, tense: str):
        return lambda p: first(aux.paradigm, tense, p)

    def const(word: str):
        return lambda p: word

    recipes = {
        EN.PROG_PRS: (finite(be, IND_PRS), ing),
        EN.PROG_PST: (finite(be, IND_PST), ing),
        EN.FUT: (const("will"), base),
        EN.FUT_PROG: (const("will be"), ing),
        EN.COND: (const("would"), base),
        EN.COND_PROG: (const("would be"), ing),
        EN.PRF_PRS: (finite(have, IND_PRS), pp),
        EN.PRF_PST: (const("had"), pp),
        EN.PRF_FUT: (const("will have"), pp),
        EN.PRF_COND: (const("would have"), pp),
        EN.PRF_PROG_PRS: (lambda p: f"{first(have.paradigm, IND_PRS, p)} been", ing),
        EN.PRF_PROG_PST: (const("had been"), ing),
    }
    tables = {}
    for key, (aux, main) in recipes.items():
        rows = []
        for p in PERSONS:
            form = f"{aux(p)} {main}"
            rows.append(Cell(p, subject(spec, verb, key, p, form), form))
        tables[key] = rows
    tables[EN.PRF_INF] = [Cell(None, "", f"to have {pp}")]
    return tables


def conjugate(db: DB, verb: Verb, aux: str | None = None) -> Conjugation:
    spec = LANGS[verb.lang]
    options = list(verb.aux)
    chosen = aux if aux in options else (options[0] if options else None)
    conj = Conjugation(verb, spec, chosen, options, simple_tables(spec, verb))
    if verb.lang == "en":
        conj.tables.update(english_periphrastic(db, spec, verb))
    elif chosen:
        conj.tables.update(romance_compounds(db, spec, verb, chosen))
    return conj
