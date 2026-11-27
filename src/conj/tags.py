"""Map Wiktextract inflection tags onto paradigm cells."""

from __future__ import annotations

from .langs.base import (
    COND_PRS, GER, IMP, IND_FUT, IND_IPFV, IND_PLPF, IND_PRS, IND_PST, INF, INF_PERS, INF_ZU,
    PERSONS, PTCP_PRS, PTCP_PST, SBJV_FUT, SBJV_IPFV, SBJV_PRS,
)

# Rows carrying any of these tags are dropped: non-standard variants,
# periphrastic descriptions ("avoir + past participle"), table markup.
NOISE = frozenset({
    "archaic", "dialectal", "obsolete", "rare", "uncommon", "nonstandard", "Traditional",
    "multiword-construction", "negative", "table-tags", "inflection-template",
    "error-unknown-tag", "alternative", "colloquial", "poetic", "auxiliary", "misspelling",
    "informal", "humorous", "regional",
    "combined-form",  # Spanish verb + object clitic (levántame, quejarme)
    "vos-form",  # Spanish voseo (hablás): the tables keep the tú forms
})

# German-only noise: variants marked wrong or regional (a second participle "Austria").
NOISE_DE = frozenset({"proscribed", "Austria", "Southern-Germany", "Switzerland"})

_PERSON = {"first-person": "1", "second-person": "2", "third-person": "3"}
_NUMBER = {"singular": "s", "plural": "p"}


def _persons(tags: frozenset[str]) -> tuple[str, ...]:
    person = next((_PERSON[t] for t in tags if t in _PERSON), None)
    number = next((_NUMBER[t] for t in tags if t in _NUMBER), None)
    if person and number:
        return (person + number,)
    if number == "p":  # English "plural present": every plural person
        return ("1p", "2p", "3p")
    if person is None and number is None:  # English "present subjunctive"
        return PERSONS
    return ()


def cells(tags: list[str] | tuple[str, ...], lang: str | None = None) -> tuple[str, tuple[str, ...]] | None:
    """Return (tense key, persons) for a conjugation row, or None to skip it.

    Non-finite keys come back with an empty persons tuple.
    """
    t = frozenset(tags) - {"reflexive", "formal", "second-person-semantically"}
    if lang == "es":
        t -= {"informal"}  # Spanish "informal second-person" is plain tú, not slang
    if lang == "de":
        if t & NOISE_DE:
            return None
        if "subjunctive-ii" in t:
            # Weak verbs' Konjunktiv II (machte) is tagged "formal rare", since it looks
            # like the Präteritum and speech prefers the würde-form. It is still the form.
            t -= {"formal", "rare"}
    if not t or t & NOISE:
        return None

    if "infinitive-zu" in t:  # German aufzustehen
        return INF_ZU, ()
    if "infinitive" in t:
        if lang == "pt" and t & {"first-person", "second-person", "third-person"}:  # personal infinitive
            persons = _persons(t)
            return (INF_PERS, persons) if persons else None
        if t & {"first-person", "second-person", "third-person"}:  # Spanish quejarme, quejarte
            return None
        return INF, ()
    if "participle" in t:
        if "past" in t:
            if t & {"feminine", "plural"}:  # Portuguese/Spanish list all four genders/numbers
                return None
            return PTCP_PST, ()
        if "present" in t:  # French "gerund participle present" = participe présent
            return PTCP_PRS, ()
        return None
    if "gerund" in t:
        if t & {"first-person", "second-person", "third-person"}:  # Spanish quejándome
            return None
        return GER, ()

    if "imperative" in t:
        if "past" in t:  # English placeholder row ("-")
            return None
        persons = _persons(t)
        if persons == PERSONS or persons == ("1p", "2p", "3p"):  # English: no person tags
            persons = ("2s", "2p")
        return IMP, persons

    if "conditional" in t:
        key = COND_PRS
    elif "subjunctive" in t:
        if "future" in t:
            key = SBJV_FUT
        else:  # German Konjunktiv I / II are subjunctive-i / subjunctive-ii
            key = SBJV_IPFV if t & {"imperfect", "past", "subjunctive-ii"} else SBJV_PRS
    elif "imperfect" in t:
        key = IND_IPFV
    elif "pluperfect" in t:
        key = IND_PLPF
    elif "future" in t:
        key = IND_FUT
    elif "past" in t or "preterite" in t:  # FR/IT "historic past", EN simple past, ES/PT pretérito
        key = IND_PST
    elif "present" in t:
        key = IND_PRS
    else:
        return None

    persons = _persons(t)
    return (key, persons) if persons else None
