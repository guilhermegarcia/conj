# conj: notes for Claude

A terminal verb conjugator (Textual TUI plus a `-p` plain CLI) for FR/IT/EN.
The user-facing docs are in README.md. This file records the decisions and
pitfalls that the code alone doesn't make obvious.

## Commands

- `uv run pytest -q`: golden tests. They read the built DB, so build or download it first.
- `uv run conj-build --src DIR`: rebuild `src/conj/data/conj.sqlite.gz` from kaikki dumps
  (default cache `~/.cache/conj-build`, ~1.3 GB, ~30 s). It needs the `build` dependency group (wordfreq).
- `uv run conj -p <verb>`: the quickest way to check output by eye.
- `uv tool install --reinstall .`: refresh the global `conj` after changes.
- The DB is git-ignored and published as a GitHub release asset (`data-YYYY-MM-DD`).
  After a rebuild that changes data, publish a new release and update the tag in README/Desktop notes.
- The runtime unpacks the .gz into `~/Library/Caches/conj/conj-<size>-<mtime>.sqlite`.
  The cache key is size+mtime, so a rebuilt DB is picked up automatically.

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
- **English:** only ~575 irregular verbs have tables. The rest are built from the
  head forms (s3/ing/past/pp). 2s is copied from 2p (are/were, not art/wast).
  `EN_MODALS` keep only the present and past.
- **Ranking:** `score` is wordfreq Zipf×100 summed over a verb's forms (EN uses the
  first token, so phrasal "find out" counts "find"; FR/IT use the last token, so
  "me lève" counts "lève"). Pronominals and phrasal verbs get −100. It drives
  search order and compare candidates (`db.by_gloss`: gloss head rank ≤2, then score).

## Runtime architecture

- Only simple tenses are stored. `compound.py` builds compound and periphrastic
  tenses at run time from the auxiliary's own paradigm (looked up in the DB) plus
  the participle, with agreement marks: allé(e)(s), andato/a/i/e.
- Clitics: FR me/te/se with elision (`normalize.fr_elides`, which has an h-aspiré
  list), `s'en` verbs use m'en/t'en. IT mi/ti/si, -rsene uses me ne… with se n'è.
- `pronominal.py` generates FR "se X" from base X when Wiktionary has no table.
  The search hit gets a **negative id**, and `search.resolve()` turns it into a Verb.
  Always use `resolve()`, never `db.by_id(hit.id)` directly.
- Tense keys: `IND.PRS`, `SBJV.IPFV`…, compounds `PRF.<aux tense>`, English
  periphrastics in `langs/en.py`. Labels, sections and compare keys are in `langs/*.py`.
- TUI: `tui/app.py` (search → OptionList → ParadigmView grid), `tui/compare.py`
  (modal with 3 panes). Test it headlessly with `App.run_test()` + `save_screenshot()`.
  Don't send ctrl+a after `/` in a Pilot script: in an Input it moves the cursor to
  the start and drops the selection.
- Keys: `gg`/`yy` are chords done by hand (`ConjApp._second_of`, 0.8 s window); Textual
  has no multi-key bindings. In tense-jump mode (`t`) `check_action` refuses every
  action so all keys reach `on_key` as labels. While the search Input has focus only
  `TYPING_ACTIONS` may fire, so letter bindings stay typeable. Theme: Textual's
  built-in `tokyo-night` (the user's nvim is tokyonight-night).

## Known rough edges / next steps

- Compare ranking is imperfect (go → gire before andare).
- Generated pronominals aren't checked for whether the verb can be pronominal.
- English "must" shows past "must" (that's what Wiktionary lists).
- Ideas: ES/DE (`langs/xx.py` + `build.SOURCES`), quiz mode, passive voice,
  downloading the DB release on first run when it's missing.

## Environment

- Python only via uv (`uv run`, `uv add`), never pip.
- The user's shell prints a harmless `_uv_dropbox_guard: command not found`; filter it out.
- `ls`/`rm` are aliased in the user's zsh: use `command ls` / `command rm`.
