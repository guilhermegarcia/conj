"""Turn a Conjugation into plain text or Rich renderables."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text

from .compound import Conjugation


def visible_sections(conj: Conjugation, compounds: bool = True):
    """(section title, [tense keys present]) in display order."""
    for section in conj.spec.sections:
        keys = [k for k in section.keys if k in conj.tables
                and (compounds or k not in conj.spec.compound_keys)]
        if keys:
            yield section.title, keys


def header(conj: Conjugation) -> str:
    v = conj.verb
    parts = [f"{v.lemma} ({conj.spec.name})"]
    if conj.aux_options:
        aux = conj.aux_options
        parts.append("aux: " + " / ".join(f"[{a}]" if a == conj.aux else a for a in aux)
                     if len(aux) > 1 else f"aux: {aux[0]}")
    return " · ".join(parts)


def plain(conj: Conjugation, compounds: bool = True, glosses: int = 3) -> str:
    lines = [header(conj)]
    if conj.verb.glosses and glosses:
        lines += [f"  · {g}" for g in conj.verb.glosses[:glosses]]
    for title, keys in visible_sections(conj, compounds):
        lines += ["", title.upper()]
        for key in keys:
            lines.append(f"  {conj.spec.label(key)}")
            for cell in conj.tables[key]:
                lines.append(f"    {cell.pron}{cell.form}")
    return "\n".join(lines) + "\n"


def tense_table(conj: Conjugation, key: str, highlight: set[tuple[str, str | None]] = frozenset(),
                width: int | None = None) -> Table:
    is_compound = key in conj.spec.compound_keys
    table = Table(
        title=conj.spec.label(key), title_justify="left",
        title_style="bold italic" if is_compound else "bold",
        show_header=False, box=None, pad_edge=False, padding=(0, 1), width=width, expand=True,
    )
    table.add_column(no_wrap=False)
    for cell in conj.tables[key]:
        text = Text()
        text.append(cell.pron, style="dim")
        hit = (key, cell.person) in highlight
        text.append(cell.form, style="reverse bold" if hit else ("" if not is_compound else "italic"))
        table.add_row(text)
    return table


def describe(conj: Conjugation, cells: list[tuple[str, str | None]]) -> str:
    """'Simple past (all persons), Past subjunctive (all persons)' / 'Presente 1s, 3p'."""
    by_tense: dict[str, list[str]] = {}
    for tense, person in cells:
        by_tense.setdefault(tense, [])
        if person:
            by_tense[tense].append(person)
    parts = []
    for tense, persons in by_tense.items():
        label = conj.spec.label(tense)
        if not persons:
            parts.append(label)
        elif len(persons) == len(conj.tables[tense]) and len(persons) > 2:
            parts.append(f"{label} (all persons)")
        else:
            parts.append(f"{label} {', '.join(persons)}")
    return "; ".join(parts)
