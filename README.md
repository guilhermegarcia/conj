# conj

`conj` conjugates French, Italian, Spanish, Portuguese and English verbs in the terminal. It shows
every simple and compound tense, and its verb data comes from open
Wiktionary data.

```
conj                 # open the TUI
conj venir           # open the TUI on a verb
conj vengo           # inflected forms work too: vengo -> venire
conj -p fr aller     # print the paradigm to stdout (no TUI)
conj -p it correre -a avere   # choose the auxiliary for compound tenses
conj -p pt falar     # also es / pt
conj -p -s went      # simple tenses only
```

## Features

- **Coverage:** about 7,500 French, 13,000 Italian, 8,900 Spanish, 6,400
  Portuguese and 57,000 English verbs. You get every simple tense, plus
  compound tenses built from the right auxiliary with participle agreement
  (*je suis allé(e)*, *noi siamo andati/e*, *he hablado*, *tenho falado*).
  Spanish and Portuguese include the future subjunctive and the negative
  imperative; Portuguese adds the personal infinitive and the simple pluperfect.
- **Pronominal verbs:** *se lever*, *s'en aller*, *alzarsi*, *andarsene* and
  *quejarse* all work. A French pronominal that has no table of its own is generated from
  its base verb.
- **Dual auxiliaries:** verbs like *correre* or *monter* offer both
  auxiliaries. Press `a` to switch.
- **Reverse lookup:** type any form (*parlerions*, *fusse*, *went*) and the
  matching cell is highlighted.
- **Compare view (`x`):** shows the same meaning in all five languages
  side by side, matched through Wiktionary's English glosses.
- **Search:** fuzzy and accent-insensitive (`allr` → *aller*, `parlo` →
  *parlò*). Prefix a query with `fr:`, `it:`, `es:`, `pt:` or `en:` to restrict it.

### Keys

| Key | Action |
|---|---|
| type, `↓`, `Enter` | search, move to the results, open a verb |
| `Esc` | leave the search box (so `Esc` `q` quits) |
| `/` | back to the search box |
| `c` | show/hide compound tenses |
| `a` | switch auxiliary (dual-auxiliary verbs) |
| `x` | compare FR / IT / ES / PT / EN (`o` opens the focused pane's verb, `Esc` closes) |
| `j` / `k`, `Ctrl-d` / `Ctrl-u` | down / up (results list or paradigm, whichever has focus) |
| `gg` / `G` | first / last result, or top / bottom of the paradigm |
| `H` | hide/show the results sidebar |
| `t` + letter | jump to a tense (each tense shows its letter; `Esc` cancels) |
| `yy` | copy the selected tense, or the whole paradigm if none is selected |
| `Y` | copy the whole paradigm as plain text |
| `F1`–`F6` | language filter: fr / it / es / pt / en / all |
| `q` | quit |

## Install

You need [uv](https://docs.astral.sh/uv/). The verb database isn't in git, so
you either download the prebuilt one or build it yourself.

```sh
git clone https://github.com/guilhermegarcia/conj.git
cd conj

# Prebuilt database (~33 MB) from the latest data release
curl -L -o src/conj/data/conj.sqlite.gz \
  https://github.com/guilhermegarcia/conj/releases/download/data-2026-11-23b/conj.sqlite.gz

uv tool install .          # installs `conj` on your PATH, with the database
```

To build the database yourself instead of downloading it, run
`uv run conj-build` before `uv tool install .`. It downloads about 250 MB of
gzip-compressed Wiktextract dumps (2.4 GB unpacked), caches them in `~/.cache/conj-build` (`--refresh` fetches
fresh copies), and builds the database in about 30 s.

The database lives at `src/conj/data/conj.sqlite.gz` and is git-ignored. On
first run `conj` unpacks it into `~/Library/Caches/conj` (or
`$XDG_CACHE_HOME/conj`). To update later, run `git pull`, download the newest
`data-*` release from the
[releases page](https://github.com/guilhermegarcia/conj/releases), and run
`uv tool install --reinstall .`.

## Development

```sh
uv run pytest              # golden tests against the built database
```

The code is organized as follows:

| Module | Role |
|---|---|
| `build.py` | Wiktextract JSONL → SQLite (tag mapping in `tags.py`, spelling in `normalize.py`) |
| `langs/` | per-language labels, pronouns, sections, compound tenses |
| `compound.py` | compound and periphrastic tenses, agreement, clitics |
| `pronominal.py` | French pronominals generated from the base verb |
| `search.py`, `compare.py` | lookup and cross-language equivalents |
| `tui/` | Textual app |

To add a language, write `langs/xx.py` and add a source to `build.SOURCES`.
Any language with Wiktionary conjugation tables (German, Catalan…) can be
added this way.

## License

The code is MIT (`LICENSE`). The verb data is CC BY-SA 4.0, from Wiktionary
contributors via Wiktextract (`DATA_LICENSE.md`).
