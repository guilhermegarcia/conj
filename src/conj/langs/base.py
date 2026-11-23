"""Language-independent paradigm vocabulary."""

from __future__ import annotations

from dataclasses import dataclass, field

PERSONS: tuple[str, ...] = ("1s", "2s", "3s", "1p", "2p", "3p")

# Simple (synthetic) tenses, as stored in the database.
IND_PRS = "IND.PRS"
IND_IPFV = "IND.IPFV"
IND_PST = "IND.PST"  # passé simple / passato remoto / English simple past
IND_FUT = "IND.FUT"
COND_PRS = "COND.PRS"
SBJV_PRS = "SBJV.PRS"
SBJV_IPFV = "SBJV.IPFV"
IMP = "IMP"
FINITE = (IND_PRS, IND_IPFV, IND_PST, IND_FUT, COND_PRS, SBJV_PRS, SBJV_IPFV, IMP)

# Non-finite forms: a single string list, no persons.
INF = "INF"
GER = "GER"
PTCP_PRS = "PTCP.PRS"
PTCP_PST = "PTCP.PST"
NONFINITE = (INF, GER, PTCP_PRS, PTCP_PST)


def compound(aux_tense: str) -> str:
    """Key of the compound tense built on `aux_tense` of the auxiliary."""
    return f"PRF.{aux_tense}"


@dataclass(frozen=True)
class Section:
    title: str
    keys: tuple[str, ...]


@dataclass(frozen=True)
class LangSpec:
    code: str
    name: str
    pronouns: dict[str, str]
    labels: dict[str, str]
    sections: tuple[Section, ...]
    # Tenses whose cells get a prefix, e.g. "que" for the French subjunctive.
    prefixes: dict[str, str] = field(default_factory=dict)
    # Keys that are compound (hidden when compounds are toggled off).
    compound_keys: frozenset[str] = frozenset()
    # Tense keys shown in the side-by-side compare view.
    compare_keys: tuple[str, ...] = ()

    def label(self, key: str) -> str:
        return self.labels.get(key, key)
