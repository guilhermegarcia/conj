"""Textual TUI: search on top, results on the left, paradigm on the right."""

from __future__ import annotations

import shutil
import subprocess
import time

from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.timer import Timer
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from ..compound import Conjugation, conjugate
from ..db import DB
from ..langs import LANGS
from ..render import header, plain, plain_tense
from ..search import Hit, resolve, search
from .compare import CompareScreen
from .widgets import ParadigmView

LANG_CYCLE = (None, "fr", "it", "en")
CHORD_TIMEOUT = 0.8  # seconds allowed between the two keys of gg / yy
THEME = "tokyo-night"  # Textual's built-in port of tokyonight (night variant)
# Actions allowed while the search box has focus (the rest are letters you type).
TYPING_ACTIONS = {"focus_search", "lang", "command_palette", "hard_quit"}

WELCOME = """\
[b]conj[/b] · French · Italian · English verb conjugation

Type a verb ([i]parler[/i]), an inflected form ([i]vengo[/i], [i]went[/i]),
or a pronominal ([i]se lever[/i]). Prefix [b]fr:[/b] [b]it:[/b] [b]en:[/b] to restrict a search.

[b]↓[/b]/[b]Enter[/b] leave the search box · [b]/[/b] or [b]Esc[/b] back to it
[b]j[/b]/[b]k[/b] down/up · [b]gg[/b]/[b]G[/b] top/bottom (results list or paradigm) · [b]H[/b] hide the sidebar
[b]t[/b] then a letter: jump to a tense · [b]yy[/b] copy that tense (or the paradigm) · [b]Y[/b] copy the paradigm
[b]c[/b] compound tenses · [b]a[/b] switch auxiliary · [b]x[/b] compare FR/IT/EN
[b]F1–F4[/b] language filter (fr / it / en / all) · [b]q[/b] quit

[dim]Data: Wiktionary (via Wiktextract), CC BY-SA 4.0.[/dim]
"""


class ConjApp(App):
    TITLE = "conj"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("escape", "focus_search", "Search", show=False),
        Binding("c", "toggle_compounds", "Compounds"),
        Binding("a", "cycle_aux", "Auxiliary"),
        Binding("x", "compare", "Compare"),
        Binding("t", "jump", "Tense"),
        Binding("y", "yank", "Copy", key_display="yy"),
        Binding("Y", "copy_all", "Copy all", show=False),
        Binding("H", "toggle_side", "Sidebar", key_display="H"),
        Binding("j", "move(1)", "Down", show=False),
        Binding("k", "move(-1)", "Up", show=False),
        Binding("ctrl+d", "move(10)", "Half page down", show=False),
        Binding("ctrl+u", "move(-10)", "Half page up", show=False),
        Binding("g", "top", "Top", show=False),
        Binding("G", "bottom", "Bottom", show=False),
        Binding("f1", "lang('fr')", "FR", show=False),
        Binding("f2", "lang('it')", "IT", show=False),
        Binding("f3", "lang('en')", "EN", show=False),
        Binding("f4", "lang('all')", "All", show=False),
        Binding("q", "quit", "Quit"),
        # Separate action so ctrl+q passes check_action while the search box has focus.
        Binding("ctrl+q", "hard_quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, db: DB, query: str = "", lang: str | None = None):
        super().__init__()
        self.db = db
        self.initial_query = query
        self.lang = lang
        self.hits: list[Hit] = []
        self.current: Hit | None = None
        self.conj: Conjugation | None = None
        self.show_compounds = True
        self._debounce: Timer | None = None
        self._chord: tuple[str, float] | None = None  # first key of gg / yy, and when
        self.jumping = False  # waiting for a tense label after `t`

    # ------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield Input(placeholder="verb or form… (fr: it: en: to filter)", id="search")
            yield Static(id="langbar")
        with Horizontal(id="body"):
            with Vertical(id="side"):
                yield OptionList(id="results")
                yield Static(id="sidehelp")
            with VerticalScroll(id="main"):
                yield Static(WELCOME, id="welcome")
                yield ParadigmView(id="paradigm")
        yield Footer()

    def on_mount(self) -> None:
        self.theme = THEME
        self.query_one("#paradigm").display = False
        self._update_langbar()
        search_box = self.query_one("#search", Input)
        search_box.focus()
        if self.initial_query:
            search_box.value = self.initial_query
            self.run_search(self.initial_query, select_first=True)

    def _update_langbar(self) -> None:
        bar = Text()
        for code in LANG_CYCLE:
            label = code or "all"
            on_ = code == self.lang
            bar.append(f" {label} ", style="reverse bold" if on_ else "dim")
        self.query_one("#langbar", Static).update(bar)

    # ------------------------------------------------------------ search
    @on(Input.Changed, "#search")
    def _typed(self, event: Input.Changed) -> None:
        if self._debounce:
            self._debounce.stop()
        self._debounce = self.set_timer(0.12, lambda: self.run_search(event.value))

    @on(Input.Submitted, "#search")
    def _submitted(self, event: Input.Submitted) -> None:
        if self._debounce:
            self._debounce.stop()
        self.run_search(event.value, select_first=True)
        if self.hits:
            self.query_one("#main").focus()

    def on_key(self, event) -> None:
        if self.jumping:
            event.stop()
            event.prevent_default()
            self._end_jump(event.character)
            return
        if event.key == "down" and self.focused is self.query_one("#search"):
            results = self.query_one("#results", OptionList)
            if results.option_count and self.query_one("#side").display:
                results.focus()
                event.stop()
            elif self.hits:
                self.query_one("#main").focus()
                event.stop()

    @work(exclusive=True, thread=True, group="search")
    def run_search(self, text: str, select_first: bool = False) -> None:
        hits = search(self.db, text, self.lang, limit=40) if text.strip() else []
        self.call_from_thread(self._show_hits, hits, select_first or bool(hits))

    def _show_hits(self, hits: list[Hit], select_first: bool) -> None:
        self.hits = hits
        results = self.query_one("#results", OptionList)
        results.set_options(self._option(h) for h in hits)
        self.query_one("#sidehelp", Static).update(
            f"[dim]{len(hits)} match{'es' if len(hits) != 1 else ''}[/dim]" if hits else
            ("[dim]no match[/dim]" if self.query_one('#search', Input).value.strip() else ""))
        if hits and select_first:
            results.highlighted = 0
            self.show(hits[0])

    @staticmethod
    def _option(hit: Hit) -> Option:
        text = Text(hit.lemma)
        text.append(f"  {hit.lang}", style="dim")
        if hit.via == "form":
            text.append(f"  ← {hit.form}", style="italic dim")
        elif hit.via == "pronominal":
            text.append("  (gen.)", style="dim")
        elif hit.via == "fuzzy":
            text.append("  ~", style="dim")
        return Option(text)

    @on(OptionList.OptionHighlighted, "#results")
    def _highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if 0 <= event.option_index < len(self.hits):
            self.show(self.hits[event.option_index])

    @on(OptionList.OptionSelected, "#results")
    def _selected(self, event: OptionList.OptionSelected) -> None:
        self.query_one("#main").focus()

    # ------------------------------------------------------------ paradigm
    def show(self, hit: Hit, aux: str | None = None) -> None:
        if hit == self.current and aux is None and self.conj is not None:
            return
        self.current = hit
        self.conj = conjugate(self.db, resolve(self.db, hit), aux)
        self._render()

    def _render(self) -> None:
        if self.conj is None:
            return
        self.query_one("#welcome").display = False
        view = self.query_one("#paradigm", ParadigmView)
        view.display = True
        highlight = set(self.conj.find(self.current.form)) if self.current and self.current.form else set()
        view.show(self.conj, compounds=self.show_compounds, highlight=highlight,
                  generated=bool(self.current and self.current.via == "pronominal"))
        self.query_one("#main", VerticalScroll).scroll_home(animate=False)

    # ------------------------------------------------------------ actions
    def action_hard_quit(self) -> None:
        self.exit()

    def action_focus_search(self) -> None:
        box = self.query_one("#search", Input)
        box.focus()
        box.select_all()  # typing replaces the previous query

    def action_toggle_compounds(self) -> None:
        self.show_compounds = not self.show_compounds
        self._render()
        self.notify("compound tenses " + ("shown" if self.show_compounds else "hidden"), timeout=1.5)

    def action_cycle_aux(self) -> None:
        conj = self.conj
        if not conj or len(conj.aux_options) < 2:
            self.notify("this verb has a single auxiliary", timeout=1.5)
            return
        i = conj.aux_options.index(conj.aux)
        aux = conj.aux_options[(i + 1) % len(conj.aux_options)]
        self.show(self.current, aux=aux)
        self.notify(f"auxiliary: {aux}", timeout=1.5)

    def action_lang(self, code: str) -> None:
        self.lang = None if code == "all" else code
        self._update_langbar()
        self.run_search(self.query_one("#search", Input).value, select_first=True)

    def action_compare(self) -> None:
        if self.conj:
            self.push_screen(CompareScreen(self.db, self.conj.verb), self._from_compare)

    def _from_compare(self, verb_hit: Hit | None) -> None:
        if verb_hit:
            self.query_one("#search", Input).value = f"{verb_hit.lang}:{verb_hit.lemma}"
            self.show(verb_hit)

    # ------------------------------------------------------------ vim motions
    def _second_of(self, key: str) -> bool:
        """True when `key` completes a chord (gg, yy); otherwise remember it as the first key."""
        now = time.monotonic()
        if self._chord and self._chord[0] == key and now - self._chord[1] < CHORD_TIMEOUT:
            self._chord = None
            return True
        self._chord = (key, now)
        return False

    def _in_results(self) -> OptionList | None:
        results = self.query_one("#results", OptionList)
        return results if self.focused is results else None

    def action_move(self, delta: int) -> None:
        if results := self._in_results():
            step = results.action_cursor_down if delta > 0 else results.action_cursor_up
            for _ in range(abs(delta)):
                step()
            return
        main = self.query_one("#main", VerticalScroll)
        if abs(delta) == 1:
            main.scroll_relative(y=2 * delta, animate=False)
        else:
            main.scroll_relative(y=(main.size.height // 2) * (1 if delta > 0 else -1), animate=False)

    def action_top(self) -> None:
        if not self._second_of("g"):
            return
        if results := self._in_results():
            results.action_first()
        else:
            self.query_one("#main", VerticalScroll).scroll_home(animate=False)

    def action_bottom(self) -> None:
        if results := self._in_results():
            results.action_last()
        else:
            self.query_one("#main", VerticalScroll).scroll_end(animate=False)

    def action_toggle_side(self) -> None:
        side = self.query_one("#side")
        side.display = not side.display
        if not side.display and self.focused is self.query_one("#results"):
            self.query_one("#main").focus()

    # ------------------------------------------------------------ tense jump / yank
    def action_jump(self) -> None:
        if not self.conj:
            return
        self.jumping = True
        self.query_one("#main").focus()
        self.query_one("#paradigm", ParadigmView).show_hints(True)
        self.refresh_bindings()

    def _end_jump(self, char: str | None) -> None:
        self.jumping = False
        view = self.query_one("#paradigm", ParadigmView)
        view.show_hints(False)
        self.refresh_bindings()
        key = view.hints().get(char or "")
        if key is None:
            return  # Esc or any other key cancels
        widget = view.select(key)
        if widget is not None:
            self.query_one("#main", VerticalScroll).scroll_to_widget(widget, animate=False)

    def action_yank(self) -> None:
        if not self.conj or not self._second_of("y"):
            return
        key = self.query_one("#paradigm", ParadigmView).selected
        if key is None:
            self.action_copy_all()
            return
        self._to_clipboard(plain_tense(self.conj, key))
        self.notify(f"copied {self.conj.verb.lemma} · {self.conj.spec.label(key)}", timeout=1.5)

    def action_copy_all(self) -> None:
        if not self.conj:
            return
        self._to_clipboard(plain(self.conj, compounds=self.show_compounds))
        self.notify(f"copied {header(self.conj).split(' · ')[0]}", timeout=1.5)

    def _to_clipboard(self, text: str) -> None:
        if shutil.which("pbcopy"):
            subprocess.run(["pbcopy"], input=text.encode(), check=False)
        else:
            self.copy_to_clipboard(text)

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if self.jumping:
            return False  # every key goes to on_key as a tense label
        # Letter bindings must not fire while typing in the search box.
        if isinstance(self.focused, Input) and action not in TYPING_ACTIONS:
            return False
        return True


__all__ = ["ConjApp", "LANGS"]
