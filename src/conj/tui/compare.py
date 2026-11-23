"""Side-by-side FR / IT / EN view of one meaning."""

from __future__ import annotations

from rich.console import Group
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Select, Static

from ..compare import equivalents
from ..compound import conjugate
from ..db import DB, Verb
from ..langs import LANGS
from ..render import tense_table
from ..search import Hit
from .widgets import verb_header

ORDER = ("fr", "it", "en")


class Pane(VerticalScroll):
    def __init__(self, db: DB, lang: str, candidates: list[Verb]):
        super().__init__(classes="pane")
        self.db, self.lang, self.candidates = db, lang, candidates
        self.verb: Verb | None = candidates[0] if candidates else None

    def compose(self) -> ComposeResult:
        spec = LANGS[self.lang]
        if self.candidates:
            yield Select([(v.lemma, i) for i, v in enumerate(self.candidates)], value=0,
                         allow_blank=False, compact=True)
        else:
            yield Static(f"[dim]no {spec.name} equivalent found[/dim]")
        yield Static(classes="pane-body")

    def on_mount(self) -> None:
        self.refresh_body()

    @on(Select.Changed)
    def _changed(self, event: Select.Changed) -> None:
        if isinstance(event.value, int):
            self.verb = self.candidates[event.value]
            self.refresh_body()

    def refresh_body(self) -> None:
        body = self.query_one(".pane-body", Static)
        if self.verb is None:
            body.update("")
            return
        conj = conjugate(self.db, self.verb)
        parts: list = [verb_header(conj)]
        for key in conj.spec.compare_keys:
            if key in conj.tables:
                parts += [Text(""), tense_table(conj, key)]
        body.update(Group(*parts))


class CompareScreen(ModalScreen[Hit | None]):
    BINDINGS = [
        Binding("escape,x,q", "dismiss_none", "Back"),
        Binding("o", "open", "Open focused verb"),
    ]

    def __init__(self, db: DB, verb: Verb):
        super().__init__()
        self.db, self.verb = db, verb

    def compose(self) -> ComposeResult:
        eq = equivalents(self.db, self.verb, ORDER)
        with Horizontal(id="compare"):
            for lang in ORDER:
                yield Pane(self.db, lang, eq.get(lang, []))
        yield Footer()

    def action_dismiss_none(self) -> None:
        self.dismiss(None)

    def action_open(self) -> None:
        node = self.focused
        while node is not None and not isinstance(node, Pane):
            node = node.parent
        if isinstance(node, Pane) and node.verb:
            v = node.verb
            self.dismiss(Hit(v.id, v.lang, v.lemma, "lemma"))
