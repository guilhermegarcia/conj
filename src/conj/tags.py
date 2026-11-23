"""Map Wiktextract inflection tags onto paradigm cells."""

from __future__ import annotations

from .langs.base import (
    COND_PRS, GER, IMP, IND_FUT, IND_IPFV, IND_PRS, IND_PST, INF, PERSONS, PTCP_PRS, PTCP_PST,
    SBJV_IPFV, SBJV_PRS,
)

# Rows carrying any of these tags are dropped: non-standard variants,
# periphrastic descriptions ("avoir + past participle"), table markup.
NOISE = frozenset({
    "archaic", "dialectal", "obsolete", "rare", "uncommon", "nonstandard", "Traditional",
    "multiword-construction", "negative", "table-tags", "inflection-template",
    "error-unknown-tag", "alternative", "colloquial", "poetic", "auxiliary", "misspelling",
    "informal", "humorous", "regional",
})

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


def cells(tags: list[str] | tuple[str, ...]) -> tuple[str, tuple[str, ...]] | None:
    """Return (tense key, persons) for a conjugation row, or None to skip it.

    Non-finite keys come back with an empty persons tuple.
    """
    t = frozenset(tags) - {"reflexive", "formal", "second-person-semantically"}
    if not t or t & NOISE:
        return None

    if "infinitive" in t:
        return INF, ()
    if "participle" in t:
        if "past" in t:
            return PTCP_PST, ()
        if "present" in t:  # French "gerund participle present" = participe présent
            return PTCP_PRS, ()
        return None
    if "gerund" in t:
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
        key = SBJV_IPFV if ("imperfect" in t or "past" in t) else SBJV_PRS
    elif "imperfect" in t:
        key = IND_IPFV
    elif "future" in t:
        key = IND_FUT
    elif "past" in t:  # "historic past" (FR/IT) or English simple past
        key = IND_PST
    elif "present" in t:
        key = IND_PRS
    else:
        return None

    persons = _persons(t)
    return (key, persons) if persons else None
