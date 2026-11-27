# conj: notes for Claude

**Conjugo** (command `conj`, package/repo `conj`), by Guilherme D. Garcia: a terminal verb
conjugator (Textual TUI plus a `-p` plain CLI) for FR/IT/ES/PT/EN. The display name and
author live in `conj/__init__.py` (`NAME`, `AUTHOR`); the README credits Claude Code.
`docs/screenshot.svg` (es:hablar, 140×40) and `docs/help.svg` (home page, 110×32) are
Textual `save_screenshot()`s; regenerate both after visible UI changes. `docs/nvim.svg` (the
Neovim float on "suis") comes from `scripts/nvim_screenshot.{lua,py}` (headless Neovim dump,
drawn with Rich; the steps are in the .py docstring); regenerate it after plugin UI changes.
The user-facing docs are in README.md. This file records the decisions and
pitfalls that the code alone doesn't make obvious.

## Commands

- `uv run pytest -q`: golden tests. They read the built DB, so build or download it first.
- `uv run conj-build --src DIR`: rebuild `src/conj/data/conj.sqlite.gz` from kaikki dumps
  (default cache `~/.cache/conj-build`, ~2.4 GB unpacked, ~30 s). Downloads ask for gzip
  (`Accept-Encoding`): ~10x smaller. Without it kaikki trickles at ~100 KB/s. It needs the `build` dependency group (wordfreq).
- `uv run conj -p <verb>`: the quickest way to check output by eye.
- `uv tool install --reinstall .`: refresh the global `conj` after changes.
- `conj --json` (`cli.print_json`, `render.as_dict`) is the contract of the Neovim plugin
  (`lua/conjugo/`, `plugin/conjugo.lua`, `doc/conjugo.txt`, at the repo root so lazy.nvim
  installs it from GitHub). Keep its keys stable. It accepts exact matches only (an
  inflected form, a lemma, a pronominal), never prefix or fuzzy hits. Multi-word forms
  (me lève, ai parlé) aren't in the reverse index, so the plugin looks up single words. Test
  the plugin headlessly: `nvim --headless -u NONE --cmd "set rtp+=."` + `lookup{on_open=…}`.
- The DB is git-ignored and published as a GitHub release asset (`data-YYYY-MM-DD`).
  `db.DATA_TAG` + `db.DATA_SHA256` pin the release each code version reads.
- DB lookup (`db.db_path`): `$CONJ_DB`; else cache `conj-<DATA_TAG>.sqlite`; else the packaged
  `src/conj/data/conj.sqlite.gz` **only if its sha256 is DATA_SHA256** (a stale copy is ignored
  with a stderr note); else download: plain HTTPS (`CONJ_DB_URL` overrides; tests use file://),
  and on 401/403/404 `gh release download` (a fallback from when the repo was private; public since 2026-11-23).
- **After `conj-build` the new DB is ignored until the pin changes.** So: build, set
  DATA_TAG (new tag, never replace an asset) and DATA_SHA256 (printed by conj-build), test,
  commit, push, `gh release create`, update the tag in the Desktop notes. Or test a build
  first with `CONJ_DB=<unpacked .sqlite>`.
- The runtime unpacks into `~/Library/Caches/conj/conj-<DATA_TAG>.sqlite`; unpacking deletes
  the other `conj-*.sqlite` files.

## Data decisions (don't relitigate without reason)

- **The source is Wiktextract/kaikki.org, not UniMorph.** UniMorph is missing basic
  verbs (être, faire, finir, prendre, parlare, be). Licensing: code MIT, data
  CC BY-SA 4.0 (see DATA_LICENSE.md). Never copy from Bescherelle, Reverso or other
  proprietary conjugators. The user explicitly wants this tool free of copyright issues.
- **Each kaikki entry can hold several conjugation tables.** `build.romance_records`
  splits rows at each `table-tags` marker and keys every table by its own
  infinitive. Pronominal tables (se laver, s'en être) are often *not* tagged
  `reflexive`. Merging them by tag was a real bug: être got aux "s'en être".
- **Italian:** Wiktionary marks stress on every word (córro, pàrla).
  `normalize.it_orthography` keeps the accent only on a final stressed vowel,
  plus the monosyllables è/dà/può. Cells keep only the *first* variant, because
  untagged regional forms (dàmo, démo, sémo) follow the standard one. An aux of
  `-` means no compound tenses (stored as `[]`).
- **French aux:** parsed from "avoir + past participle" in the first table only.
  `FR_DUAL_AUX` is a hand-written closed list (monter, sortir, passer…).
  Pronominals always take être.
- **Spanish:** tú rows are tagged `informal`, which is NOISE for FR/IT, so `cells(tags, "es")`
  strips it. `vos-form` and `combined-form` (levántame, quejarme) are dropped. Participles
  come as 4 gendered forms; only masc. sg. is kept. -se imperfect subjunctive is a second
  variant (hablara / hablase). Aux is always haber. ~255 reflexives (quejarse) have tables;
  `pronominal.py` generates the rest from the base (levantarse). When the base exists,
  `search.resolve` derives even stored -rse verbs from it: Wiktionary's reírse/despertarse
  tables miss the stem change (me reo). Enclitics keep stress via `es_enclitic`
  (levanta+te → levántate, vestid+os → vestíos, id → idos).
- **Portuguese:** person-tagged `infinitive` rows are the personal infinitive (`INF.PERS`,
  a person table in FINITE); only with lang "pt" (Spanish reflexives also list quejarme…).
  `pluperfect` → `IND.PLPF` (falara). Aux is always ter. Brazilian terminology/labels
  (subjuntivo). No -se verbs have tables; all are generated with **Brazilian placement**
  (user's choice): proclisis in finite tenses (eu me levanto, eu tenho me levantado),
  enclisis in the affirmative imperative and citation forms (levante-se, levantar-se,
  ter-se levantado). Search accepts levantar-se, "levantar se", or levantarse with pt:.
- **ES/PT shared:** `future subjunctive` → `SBJV.FUT`. The negative imperative (`IMP.NEG`)
  is not stored: `compound.simple_tables` builds it from SBJV.PRS (no hables, não fales).
  `Conjugation.find` prefers accent-exact matches (hablé ≠ hable).
- **German (added 2026-11-27):** tags `preterite` → IND.PST, `subjunctive-i` → SBJV.PRS,
  `subjunctive-ii` → SBJV.IPFV, `infinitive-zu` → INF.ZU (built as "zu X" when missing:
  Wiktionary gives it for separable verbs only). Weak verbs' Konjunktiv II is tagged
  `formal rare` (same as the Präteritum): `cells` strips those two tags for de, or weak
  verbs lose the tense. `NOISE_DE` drops `proscribed` and regional rows. Aux from the
  `auxiliary` rows ("haben or sein"); dual-aux verbs put sein first (user-facing default:
  ich bin aufgestanden). Separable verbs: tables show main-clause forms (stehe auf);
  `subordinate-clause` rows (aufstehe) go to the hidden `SEARCH` list key, indexed but
  never displayed. `frequency` uses the FIRST token for de (the particle "auf" would
  swamp the score). `fold` maps ß → ss. `compound.german_tables` builds Perfekt etc. from
  aux + Partizip II, Futur I/II and the würde-form from werden, the perfect infinitive
  participle-first (gegangen sein), and imperative wir/Sie rows from Konjunktiv I with
  the pronoun after the verb (stehen Sie auf). Section "Infinite Formen".
  Reflexives: Wiktionary has no German reflexive tables (only 43 stored "sich …" idioms),
  so "sich X" is generated from X like the FR/ES/PT pronominals (`pronominal._de`,
  `search` step 0a, negative ids): pronoun after the finite verb, before a particle
  (ich ziehe mich an), always haben (beeilen lists sein), accusative only (mich: the
  dative reflexives can't be told from the data). `german_tables` puts the pronoun
  after the auxiliary (habe mich gefreut, werde mich freuen, sich gefreut haben).
  Ranking: `frequency` counts only one-word German forms (infinitive, participles,
  SEARCH forms); multiword main-clause forms scored separable verbs as their base
  (freihaben as haben). Homographs still inflate (freien via the adjective frei).
- **IPA:** some kaikki FR rows hold IPA as the form (paʁl); `_clean` drops U+0250–02AF.
- **English:** only ~575 irregular verbs have tables. The rest are built from the
  head forms (s3/ing/past/pp). 2s is copied from 2p (are/were, not art/wast).
  `EN_MODALS` keep only the present and past.
- **Ranking:** `score` is wordfreq Zipf×100 summed over a verb's forms (EN uses the
  first token, so phrasal "find out" counts "find"; FR/IT use the last token, so
  "me lève" counts "lève"). Pronominals (`PRONOMINAL_ENDINGS`) and phrasal verbs get −100. It drives
  search order.

## Runtime architecture

- Only simple tenses are stored. `compound.py` builds compound and periphrastic
  tenses at run time from the auxiliary's own paradigm (looked up in the DB) plus
  the participle, with agreement marks: allé(e)(s), andato/a/i/e. ES/PT: no agreement.
- Clitics: ES me/te/se/nos/os before the aux; haberse, habiéndose. FR me/te/se with elision (`normalize.fr_elides`, which has an h-aspiré
  list), `s'en` verbs use m'en/t'en. IT mi/ti/si, -rsene uses me ne… with se n'è.
- `pronominal.py` generates FR "se X", ES "Xse", PT "X-se" from base X when Wiktionary has no table.
  The search hit gets a **negative id**, and `search.resolve()` turns it into a Verb.
  Always use `resolve()`, never `db.by_id(hit.id)` directly.
- Tense keys: `IND.PRS`, `SBJV.IPFV`…, compounds `PRF.<aux tense>`, English
  periphrastics in `langs/en.py`. Labels and sections are in `langs/*.py`.
- TUI: `tui/app.py` (search → OptionList → ParadigmView grid). Test it headlessly with `App.run_test()` + `save_screenshot()`.
  Don't send ctrl+a after `/` in a Pilot script: in an Input it moves the cursor to
  the start and drops the selection.
- Keys: `1`–`6` language filter (fr it es pt en de), `0` all (not F-keys: Mac). Textual never checks printable
  bindings while an Input has focus, even `priority=True` ones, so `SearchInput._on_key`
  turns digits into `action_lang` itself. `?` toggles the welcome page and the paradigm.
  Footer: `Footer(compact=True, show_command_palette=False)`, and `^h/^l`, `j/k` shown as one
  entry per pair (`key_display`), so the key list fits 80 columns (worst case ~78, a
  dual-auxiliary verb). `H`, `t` and `Ctrl-p` are on the help page only; `a` and `D` are
  hidden by `check_action` when they can't act (single auxiliary; no `lexis` on PATH), and
  `_render` calls `refresh_bindings()` so the footer follows the verb shown.
  Panes: `Ctrl-h`/`Ctrl-l` (as in Lexis, whose entry pane needs h/l for its cursor), with
  `h`/`l` kept as aliases. Textual parses Ctrl-h (`\x08`) as `backspace`: bind both. Measure with `FooterKey.region` before adding a
  footer key (compact mode still puts 1 column between keys). Lexis (`~/Repos/lexis`)
  mirrors this TUI; keep the two in step.
  `q` opens `QuitScreen` (y/q/Enter quit, n/Esc stay); while it is up `check_action`
  refuses app actions except `hard_quit` (Ctrl-q).
  `h`/`l` (and ←/→) focus results/paradigm; `j`/`k` act on the focused pane
  (`action_move` checks `_in_results`). `gg`/`yy` are chords done by hand (`ConjApp._second_of`, 0.8 s window); Textual
  has no multi-key bindings. In tense-jump mode (`t`) `check_action` refuses every
  action so all keys reach `on_key` as labels. While the search Input has focus only
  `TYPING_ACTIONS` may fire, so letter bindings stay typeable. Esc only *leaves* the
  search box (`leave_search`), never returns to it, so `Esc q` always quits; `/` goes back. Theme: Textual's
  built-in `tokyo-night` (the user's nvim is tokyonight-night). The theme picker previews live:
  `search_themes` records the old theme, `CommandPalette.OptionHighlighted` applies the
  highlighted one, `CommandPalette.Closed` without a selection restores it.

## Lexis link (`link.py`)

- `D` runs `lexis --lang LANG LEMMA` under `App.suspend()`; Lexis (`~/Repos/lexis`) is a
  separate `uv tool`, so no imports. `CONJ_FROM_LEXIS` / `LEXIS_FROM_CONJ` = "lang:lemma"
  mark where each app came from; going back to that verb exits instead of nesting. Lexis's
  `C` runs `conj -j` (keep the JSON contract) and then `conj LANG FORM`.
- Opened by Lexis (`CONJ_FROM_LEXIS` set), conj starts with focus in the paradigm, not the
  search box, so `C D C D` flips between the apps (user's request); a `D` typed into the
  search box would just be text. Lexis likewise starts in its dictionary list.
- Tests stub `link.lexis_command` / `link.run_lexis` and set `app.suspend =
  contextlib.nullcontext` (the test driver can't suspend).

## Known rough edges / next steps

- A cross-language compare view (`x`, matched through English gloss heads) was removed
  2026-11-23: Wiktionary has no verb-to-verb links, and the gloss pivot was too noisy
  (go → gire, speak → dizer, eat → no PT comer). Don't re-add it on the same basis.
- Generated pronominals aren't checked for whether the verb can be pronominal. ES/PT
  generated ones show the base verb's glosses (levantarse: "to lift").
- English "must" shows past "must" (that's what Wiktionary lists).
- Ideas: quiz mode, passive voice.

## Planned: Russian (decided 2026-11-27, not started; German is done, see above)

- **Russian:** aspect from tags (imperfective/perfective) and the head template's `pf`/
  `impf` partners: show both in the header, plus a key (`p`) that opens the partner.
  Past is by gender: show it in the person table with marks (я говорил(а), он говорил /
  она говорила / оно говорило, мы говорили) (user's choice). Present for imperfectives
  only; future = буду + inf (impf) or synthetic (pf; note Wiktionary's буду rows are NOT
  tagged multiword-construction); conditional = past + бы; 4 participles + 2 adverbial
  participles. Drop `dated` (pre-1918) and `romanization` rows. Keep stress marks for
  display; `fold` strips them, but must NOT fold й → и (NFD splits й into и + breve).
  Cyrillic input only for now (user's choice; transliterated search maybe later).
  Language key 7, prefix `ru:`; add to the Neovim plugin LANGS and Lexis's
  `link.CONJ_LANGS`.
