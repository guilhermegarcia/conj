"""Textual TUI: search on top, results on the left, paradigm on the right."""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from rich.text import Text
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import CommandPalette
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.widgets import Footer, Input, OptionList, Static
from textual.widgets.option_list import Option

from .. import AUTHOR, NAME, WEBSITE, __version__, link
from ..compound import Conjugation, conjugate
from ..db import DB
from ..langs import LANGS
from ..render import header, plain, plain_tense
from ..search import Hit, resolve, search
from .layout import latin
from .widgets import ParadigmView

LANG_CYCLE = (None, "fr", "it", "es", "pt", "en", "de", "ru")
CHORD_TIMEOUT = 0.8  # seconds allowed between the two keys of gg / yy
THEME = "tokyo-night"  # Textual's built-in port of tokyonight (night variant)
# Actions allowed while the search box has focus (the rest are letters you type).
TYPING_ACTIONS = {"focus_search", "leave_search", "lang", "command_palette", "hard_quit"}

WELCOME = f"""\
[b $accent]{NAME}[/] [dim]{__version__}[/dim]
verb conjugation for French, Italian, Spanish, Portuguese and English
[dim]by {AUTHOR} • [link="https://{WEBSITE}"]{WEBSITE}[/link][/dim]

Type a verb ([i]parler[/i]), an inflected form
([i]vengo[/i], [i]went[/i]) or a pronominal ([i]se lever[/i]).
Prefix [b]fr:[/b] [b]it:[/b] [b]es:[/b] [b]pt:[/b] [b]en:[/b] to restrict a search.

[b]Esc   [/b] leave the search box
[b]/     [/b] back to the search box
[b]^h ^l [/b] results list / paradigm (h / l work too)
[b]j  k  [/b] down / up
[b]gg  G [/b] top / bottom
[b]t     [/b] jump to a tense (then its letter)
[b]yy  Y [/b] copy that tense / the paradigm
[b]c     [/b] compound tenses
[b]a     [/b] switch auxiliary
[b]p     [/b] Russian: open the aspect partner (говорить ↔ сказать)
[b]H     [/b] hide the sidebar
[b]1–7 0[/b] language: fr it es pt en de ru, 0 all
[b]?     [/b] this page / back to the verb
[b]q     [/b] quit (Ctrl-q: without asking)
[b]D     [/b] define the verb in Lexis (macOS, if installed)
[b]Ctrl-p[/b] commands, including the theme picker

[dim]Data: Wiktionary (via Wiktextract), CC BY-SA 4.0
Built with Claude Code[/dim]
"""


LANG_KEYS = {"1": "fr", "2": "it", "3": "es", "4": "pt", "5": "en", "6": "de", "7": "ru", "0": "all"}


class SearchInput(Input):
    """The search box: digits pick the language filter instead of being typed."""

    async def _on_key(self, event) -> None:
        if event.character in LANG_KEYS:
            event.stop()
            event.prevent_default()
            self.app.action_lang(LANG_KEYS[event.character])
            return
        await super()._on_key(event)


class QuitScreen(ModalScreen[bool]):
    """Asked by q. y / Enter / q again quits; n / Esc stays."""

    BINDINGS = [
        Binding("y,enter,q", "answer(True)", "Quit"),
        Binding("n,escape", "answer(False)", "Stay"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(f"Quit {NAME}?\n\n[b]y[/b] / [b]q[/b] / [b]Enter[/b] quit · [b]n[/b] / [b]Esc[/b] stay",
                     id="quit-dialog")

    def action_answer(self, quit_: bool) -> None:
        self.dismiss(quit_)


class ConjApp(App):
    TITLE = NAME
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("slash", "focus_search", "Search", key_display="/"),
        Binding("escape", "leave_search", "Leave search", show=False),
        # Footer order: search, panes, motion, then the rest. One footer entry per pair.
        # Ctrl-h / Ctrl-l as in Lexis (whose entry pane uses h / l for its cursor);
        # terminals send Ctrl-h as Backspace, hence both. h / l stay as aliases here.
        Binding("ctrl+h,backspace", "pane('results')", "Panes", key_display="^h/^l"),
        Binding("ctrl+l", "pane('main')", "Paradigm", show=False),
        Binding("h,left", "pane('results')", "Results", show=False),
        Binding("l,right", "pane('main')", "Paradigm", show=False),
        Binding("j", "move(1)", "Move", key_display="j/k"),
        Binding("k", "move(-1)", "Up", show=False),
        Binding("c", "toggle_compounds", "Compounds"),
        Binding("a", "cycle_aux", "Aux"),
        Binding("p", "partner", "Aspect"),
        Binding("t", "jump", "Tense", show=False),  # on the help page: footer space is tight
        Binding("y", "yank", "Copy", key_display="yy"),
        Binding("Y", "copy_all", "Copy all", show=False),
        Binding("D", "define", "Define", key_display="D"),
        Binding("H", "toggle_side", "Sidebar", show=False),  # on the help page; footer space is tight
        Binding("ctrl+d", "move(10)", "Half page down", show=False),
        Binding("ctrl+u", "move(-10)", "Half page up", show=False),
        Binding("g", "top", "Top", show=False),
        Binding("G", "bottom", "Bottom", show=False),
        # Digits never occur in a verb, so they switch language even while typing
        # (SearchInput passes them on; Textual skips printable bindings in an Input).
        Binding("1", "lang('fr')", "FR", show=False),
        Binding("2", "lang('it')", "IT", show=False),
        Binding("3", "lang('es')", "ES", show=False),
        Binding("4", "lang('pt')", "PT", show=False),
        Binding("5", "lang('en')", "EN", show=False),
        Binding("6", "lang('de')", "DE", show=False),
        Binding("7", "lang('ru')", "RU", show=False),
        Binding("0", "lang('all')", "All", show=False),
        Binding("question_mark", "home", "Help", key_display="?"),
        Binding("q", "ask_quit", "Quit"),
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
        self._partner_turn: dict[str, int] = {}  # p: which aspect partner comes next
        self.jumping = False  # waiting for a tense label after `t`
        self._theme_before: str | None = None  # set while the theme picker is open

    # ------------------------------------------------------------ layout
    def compose(self) -> ComposeResult:
        with Horizontal(id="top"):
            yield Static(NAME, id="brand")
            yield SearchInput(placeholder="verb or form… (fr: it: es: pt: en: to filter)", id="search")
            yield Static(id="langbar")
        with Horizontal(id="body"):
            with Vertical(id="side"):
                yield OptionList(id="results")
                yield Static(id="sidehelp")
            with VerticalScroll(id="main"):
                yield Static(WELCOME, id="welcome")
                yield ParadigmView(id="paradigm")
        # Compact, and Ctrl-p listed on the help page instead, so the keys fit 80 columns.
        yield Footer(compact=True, show_command_palette=False)

    def on_mount(self) -> None:
        self.theme = THEME
        self.query_one("#paradigm").display = False
        self._update_langbar()
        search_box = self.query_one("#search", Input)
        search_box.focus()
        if self.initial_query:
            search_box.value = self.initial_query
            self.run_search(self.initial_query, select_first=True)
            if os.environ.get(link.FROM_LEXIS):
                # Opened by Lexis's C: start in the paradigm, so D goes straight back
                # (C D C D flips between the two apps) instead of typing a "D".
                self.query_one("#main").focus()

    # ------------------------------------------------------------ theme preview
    # Textual's picker applies a theme only on Enter. Preview the highlighted one
    # instead, and put the old theme back if the picker is closed with Esc.
    def search_themes(self) -> None:
        self._theme_before = self.theme
        super().search_themes()

    @on(CommandPalette.OptionHighlighted)
    def _preview_theme(self, event: CommandPalette.OptionHighlighted) -> None:
        if self._theme_before is None:
            return  # the ordinary command palette, not the theme picker
        hit = getattr(event.highlighted_event.option, "hit", None)
        name = getattr(hit, "text", None) or str(getattr(hit, "prompt", ""))
        if name in self.available_themes and name != self.theme:
            self.theme = name

    @on(CommandPalette.Closed)
    def _end_theme_preview(self, event: CommandPalette.Closed) -> None:
        if self._theme_before is None:
            return
        if not event.option_selected:
            self.theme = self._theme_before
        self._theme_before = None

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
        self.refresh_bindings()  # a (dual auxiliary) and D depend on the verb shown

    # ------------------------------------------------------------ actions
    def action_hard_quit(self) -> None:
        self.exit()

    def action_ask_quit(self) -> None:
        self.push_screen(QuitScreen(), lambda quit_: self.exit() if quit_ else None)

    def action_focus_search(self) -> None:
        box = self.query_one("#search", Input)
        box.focus()
        box.select_all()  # typing replaces the previous query

    def action_toggle_compounds(self) -> None:
        self.show_compounds = not self.show_compounds
        self._render()
        self.notify("compound tenses " + ("shown" if self.show_compounds else "hidden"), timeout=1.5)

    def action_home(self) -> None:
        """?: show this help page; press again to go back to the verb."""
        welcome = self.query_one("#welcome")
        paradigm = self.query_one("#paradigm")
        if welcome.display and self.conj is not None:
            welcome.display, paradigm.display = False, True
        else:
            welcome.display, paradigm.display = True, False
            self.query_one("#main", VerticalScroll).scroll_home(animate=False)

    def action_leave_search(self) -> None:
        """Esc: give focus to the paradigm, so the next key is a command (Esc q quits)."""
        if isinstance(self.focused, Input):
            self.query_one("#main").focus()

    def action_cycle_aux(self) -> None:
        conj = self.conj
        if not conj or len(conj.aux_options) < 2:
            self.notify("this verb has a single auxiliary", timeout=1.5)
            return
        i = conj.aux_options.index(conj.aux)
        aux = conj.aux_options[(i + 1) % len(conj.aux_options)]
        self.show(self.current, aux=aux)
        self.notify(f"auxiliary: {aux}", timeout=1.5)

    def action_partner(self) -> None:
        """p: open the verb's aspect partner (говори́ть <-> сказа́ть).

        With several partners (говори́ть: сказа́ть, поговори́ть), each p from the
        same verb moves on to the next one, so p p cycles through them all.
        """
        conj = self.conj
        if not conj or not conj.partners:
            return
        lemma = conj.verb.lemma
        turn = self._partner_turn.get(lemma, 0)
        self._partner_turn[lemma] = turn + 1
        partner = conj.partners[turn % len(conj.partners)]
        verb = self.db.get("ru", partner.replace("\u0301", ""))
        if verb is None:
            self.notify(f"{partner} isn't in the database", timeout=1.5)
            return
        self.show(Hit(verb.id, verb.lang, verb.lemma, "lemma"))
        self.notify(f"{conj.title} → {self.conj.title}", timeout=1.5)

    def action_lang(self, code: str) -> None:
        self.lang = None if code == "all" else code
        self._update_langbar()
        self.run_search(self.query_one("#search", Input).value, select_first=True)

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

    def action_pane(self, which: str) -> None:
        """h / l: focus the results list or the paradigm; j / k then move in that pane."""
        if which == "main":
            self.query_one("#main").focus()
            return
        results = self.query_one("#results", OptionList)
        if not results.option_count:
            return
        self.query_one("#side").display = True  # h brings back a hidden sidebar
        results.focus()

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

    # ------------------------------------------------------------ Lexis link
    def action_define(self) -> None:
        """D: open Lexis on this verb, in this verb's language."""
        if not self.conj:
            return
        verb = self.conj.verb
        if link.came_from(verb.lang, verb.lemma):
            self.exit()  # opened from Lexis on this verb: go back instead of nesting
            return
        with self.suspend():
            link.run_lexis(verb.lang, verb.lemma)

    # ------------------------------------------------------------ keyboard layout
    async def on_event(self, event) -> None:
        """Cyrillic layout: a command key acts as the Latin key in its place (о = j).

        Text stays as typed: in the search box, and wherever a widget asks for the
        next character itself (raw_keys: Lexis's f/t). See layout.py.
        """
        if isinstance(event, events.Key):
            typing = isinstance(self.focused, Input) or getattr(self.focused, "raw_keys", False)
            event = latin(event, plain=not typing) or event  # Ctrl + ч is ctrl+h even when typing
        await super().on_event(event)

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if self.jumping:
            return False  # every key goes to on_key as a tense label
        if isinstance(self.screen, QuitScreen):
            return action == "hard_quit"  # only the dialog's own keys
        # Keys that can't do anything here stay out of the footer (it must fit 80 columns).
        if action == "define" and not (self.conj and link.lexis_command()):
            return False
        if action == "cycle_aux" and not (self.conj and len(self.conj.aux_options) > 1):
            return False
        if action == "partner" and not (self.conj and self.conj.partners):
            return False  # Russian verbs with an aspect partner only
        if action == "toggle_compounds" and not (self.conj and self.conj.spec.compound_keys):
            return False  # nothing to hide (Russian)
        # Letter bindings must not fire while typing in the search box.
        if isinstance(self.focused, Input) and action not in TYPING_ACTIONS:
            return False
        return True


__all__ = ["ConjApp", "LANGS"]
