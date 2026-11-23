"""Paradigm display: sections of tense tables laid out in a responsive grid."""

from __future__ import annotations

from rich.text import Text
from textual.containers import Grid, Vertical
from textual.events import Resize
from textual.widgets import Static

from ..compound import Conjugation
from ..render import tense_table, visible_sections

CELL_WIDTH = 34  # columns per tense table, including the gutter


class TenseGrid(Grid):
    def on_resize(self, event: Resize) -> None:
        self.styles.grid_size_columns = max(1, event.size.width // CELL_WIDTH)


def verb_header(conj: Conjugation, generated: bool = False) -> Text:
    v = conj.verb
    text = Text()
    text.append(v.lemma, style="bold")
    text.append(f"  {conj.spec.name}", style="dim")
    if conj.aux_options:
        text.append("   aux: ", style="dim")
        for i, aux in enumerate(conj.aux_options):
            if i:
                text.append(" / ", style="dim")
            text.append(aux, style="bold underline" if aux == conj.aux and len(conj.aux_options) > 1 else "")
        if len(conj.aux_options) > 1:
            text.append("  (a to switch)", style="dim italic")
    if generated:
        text.append("\n(pronominal forms generated from ", style="dim italic")
        text.append(v.lemma.removeprefix("se ").removeprefix("s'"), style="dim italic bold")
        text.append(")", style="dim italic")
    if v.glosses:
        for g in v.glosses[:3]:
            text.append(f"\n  · {g}", style="italic")
    return text


class ParadigmView(Vertical):
    def show(self, conj: Conjugation, compounds: bool = True,
             highlight: set[tuple[str, str | None]] | None = None, generated: bool = False) -> None:
        highlight = highlight or set()
        widgets: list = [Static(verb_header(conj, generated), classes="verb-header")]
        for title, keys in visible_sections(conj, compounds):
            widgets.append(Static(title, classes="section-title"))
            tables = [Static(tense_table(conj, k, highlight), classes="tense") for k in keys]
            widgets.append(TenseGrid(*tables, classes="tenses"))
        with self.app.batch_update():
            self.remove_children()
            self.mount_all(widgets)
