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
    from ..render import aspect_line

    v = conj.verb
    text = Text()
    text.append(conj.title, style="bold")
    text.append(f"  {conj.spec.name}", style="dim")
    if conj.aspect:
        text.append(f"   {aspect_line(conj)}", style="")
        if conj.partners:
            text.append("  (p to switch)", style="dim italic")
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
        text.append(getattr(v, "base_lemma", v.lemma), style="dim italic bold")
        text.append(")", style="dim italic")
    if v.glosses:
        for g in v.glosses[:3]:
            text.append(f"\n  · {g}", style="italic")
    return text


# Jump labels for tense-jump mode, home row first. Verbs have at most ~22 tenses.
HINT_KEYS = "asdfghjklqwertyuiopzxcvbnm"


class ParadigmView(Vertical):
    """All tenses of one verb. One tense can be *selected* (for jumping and yanking)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.conj: Conjugation | None = None
        self.highlight: set[tuple[str, str | None]] = set()
        self.tables: dict[str, Static] = {}  # tense key -> widget, in display order
        self.selected: str | None = None

    def show(self, conj: Conjugation, compounds: bool = True,
             highlight: set[tuple[str, str | None]] | None = None, generated: bool = False) -> None:
        self.conj, self.highlight = conj, highlight or set()
        self.tables = {}
        widgets: list = [Static(verb_header(conj, generated), classes="verb-header")]
        for title, keys in visible_sections(conj, compounds):
            widgets.append(Static(title, classes="section-title"))
            for k in keys:
                self.tables[k] = Static(tense_table(conj, k, self.highlight), classes="tense")
            widgets.append(TenseGrid(*(self.tables[k] for k in keys), classes="tenses"))
        if self.selected not in self.tables:
            self.selected = None  # keep the selection across verbs when the tense exists
        elif self.selected:
            self.tables[self.selected].add_class("selected")
        with self.app.batch_update():
            self.remove_children()
            self.mount_all(widgets)

    def hints(self) -> dict[str, str]:
        """Jump label -> tense key."""
        return dict(zip(HINT_KEYS, self.tables))

    def show_hints(self, on: bool) -> None:
        if self.conj is None:
            return
        labels = {k: h for h, k in self.hints().items()} if on else {}
        for key, widget in self.tables.items():
            widget.update(tense_table(self.conj, key, self.highlight, badge=labels.get(key)))

    def select(self, key: str | None) -> Static | None:
        if self.selected in self.tables:
            self.tables[self.selected].remove_class("selected")
        self.selected = key if key in self.tables else None
        if self.selected is None:
            return None
        widget = self.tables[self.selected]
        widget.add_class("selected")
        return widget
