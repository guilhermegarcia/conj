# conj

`conj` conjugates French, Italian and English verbs in the terminal. It shows
every simple and compound tense, and its verb data comes from open
Wiktionary data.

```
conj                 # open the TUI
conj venir           # open the TUI on a verb
conj vengo           # inflected forms work too: vengo -> venire
conj -p fr aller     # print the paradigm to stdout (no TUI)
conj -p it correre -a avere   # choose the auxiliary for compound tenses
conj -p -s went      # simple tenses only
```

## Features

- **Coverage:** about 7,500 French, 13,000 Italian and 57,000 English verbs.
  You get every simple tense, plus compound tenses built from the right
  auxiliary with participle agreement (*je suis allé(e)*, *noi siamo andati/e*).
- **Pronominal verbs:** *se lever*, *s'en aller*, *alzarsi* and *andarsene*
  all work. A French pronominal that has no table of its own is generated from
  its base verb.
- **Dual auxiliaries:** verbs like *correre* or *monter* offer both
  auxiliaries. Press `a` to switch.
- **Reverse lookup:** type any form (*parlerions*, *fusse*, *went*) and the
  matching cell is highlighted.
- **Compare view (`x`):** shows the same meaning in French, Italian and English
  side by side, matched through Wiktionary's English glosses.
- **Search:** fuzzy and accent-insensitive (`allr` → *aller*, `parlo` →
  *parlò*). Prefix a query with `fr:`, `it:` or `en:` to restrict it.

### Keys

| Key | Action |
|---|---|
| type, `↓`, `Enter` | search, move to the results, open a verb |
| `/`, `Esc` | back to the search box |
| `c` | show/hide compound tenses |
| `a` | switch auxiliary (dual-auxiliary verbs) |
| `x` | compare FR / IT / EN (`o` opens the focused pane's verb, `Esc` closes) |
| `j` / `k`, `Ctrl-d` / `Ctrl-u` | down / up (results list or paradigm, whichever has focus) |
| `gg` / `G` | first / last result, or top / bottom of the paradigm |
| `H` | hide/show the results sidebar |
| `t` + letter | jump to a tense (each tense shows its letter; `Esc` cancels) |
| `yy` | copy the selected tense, or the whole paradigm if none is selected |
| `Y` | copy the whole paradigm as plain text |
| `F1`–`F4` | language filter: fr / it / en / all |
| `q` | quit |

## Install

```sh
uv run conj-build          # one-time: downloads ~1.3 GB of Wiktextract dumps, builds the DB (~30 s)
uv tool install .          # installs `conj` on your PATH, with the database
```

`conj-build` caches the dumps in `~/.cache/conj-build`. Pass `--refresh` to
download fresh copies. The database (`src/conj/data/conj.sqlite.gz`, about
23 MB) is git-ignored. On first run `conj` unpacks it into
`~/Library/Caches/conj` (or `$XDG_CACHE_HOME/conj`).

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
Any language with Wiktionary conjugation tables (Spanish, German,
Portuguese…) can be added this way.

## License

The code is MIT (`LICENSE`). The verb data is CC BY-SA 4.0, from Wiktionary
contributors via Wiktextract (`DATA_LICENSE.md`).
