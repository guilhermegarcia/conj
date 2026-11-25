# Conjugo

Verb conjugation in the terminal for French, Italian, Spanish, Portuguese and
English, built on open Wiktionary data. It shows every simple and compound
tense, finds a verb from any of its forms, and runs from the `conj` command.

By **Guilherme D. Garcia**. Built with [Claude Code](https://claude.com/claude-code)
(see [How it was made](#how-it-was-made)).

![Conjugo showing the Spanish verb hablar](docs/screenshot.svg)

![Conjugo's help page with the key list](docs/help.svg)

```
conj                 # open the TUI
conj venir           # open the TUI on a verb
conj vengo           # inflected forms work too: vengo -> venire
conj -p fr aller     # print the paradigm to stdout (no TUI)
conj -p it correre -a avere   # choose the auxiliary for compound tenses
conj -p pt falar     # also es / pt
conj -p -s went      # simple tenses only
conj -j parlons      # JSON, exact matches only (used by the Neovim plugin)
```

## Features

- **Coverage:** about 7,500 French, 13,000 Italian, 8,900 Spanish, 6,400
  Portuguese and 57,000 English verbs. You get every simple tense, plus
  compound tenses built from the right auxiliary with participle agreement
  (*je suis allé(e)*, *noi siamo andati/e*, *he hablado*, *tenho falado*).
  Spanish and Portuguese include the future subjunctive and the negative
  imperative; Portuguese adds the personal infinitive and the simple pluperfect.
- **Pronominal verbs:** *se lever*, *s'en aller*, *alzarsi*, *andarsene*,
  *levantarse* and *levantar-se* all work. A French, Spanish or Portuguese
  pronominal that has no table of its own is generated from its base verb.
  Portuguese uses Brazilian clitic placement (*eu me levanto*, *eu tenho me
  levantado*, *levante-se*).
- **Dual auxiliaries:** verbs like *correre* or *monter* offer both
  auxiliaries. Press `a` to switch.
- **Reverse lookup:** type any form (*parlerions*, *fusse*, *went*) and the
  matching cell is highlighted.
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
| `h` / `l` | focus the results list / the paradigm |
| `j` / `k`, `Ctrl-d` / `Ctrl-u` | down / up in the focused pane (results list or paradigm) |
| `gg` / `G` | first / last result, or top / bottom of the paradigm |
| `H` | hide/show the results sidebar |
| `t` + letter | jump to a tense (each tense shows its letter; `Esc` cancels) |
| `yy` | copy the selected tense, or the whole paradigm if none is selected |
| `Y` | copy the whole paradigm as plain text |
| `1`–`6` | language filter: fr / it / es / pt / en / all (works while typing too) |
| `?` | home page with the key list; again to go back to the verb |
| `q` | quit (asks first: `y`/`q`/`Enter` quits, `n`/`Esc` stays); `Ctrl-q` quits at once |

## Install

You need [uv](https://docs.astral.sh/uv/). Then:

```sh
uv tool install git+https://github.com/guilhermegarcia/conj
```

That puts `conj` on your PATH. The verb database (~30 MB) isn't in git: on its
first run `conj` downloads the release made for your version of the code,
checks its SHA-256, and unpacks it into `~/Library/Caches/conj` (or
`$XDG_CACHE_HOME/conj`, by default `~/.cache/conj` on Linux). Later runs work offline.

To update, run `uv tool upgrade conj` (or, from a clone, `git pull && uv tool
install --reinstall .`). If the new version needs a newer database, it
downloads it on its next run and deletes the old one. A copy at
`src/conj/data/conj.sqlite.gz` that isn't the release the code expects is
ignored.

To try it without installing: `uvx --from git+https://github.com/guilhermegarcia/conj conj`.

### Neovim

The repo is also a Neovim plugin (0.10 or later). `:Conj` opens a floating
window with the conjugation of the verb under the cursor, with the form under
the cursor highlighted. If the word isn't a verb, you get a message instead.
The plugin only draws the window: the conjugations come from `conj --json`, so
it needs Conjugo installed (see [Install](#install)), with `conj` on your PATH.
Without it, `:Conj` reports that it cannot run `conj`. If you have uv but would
rather not install Conjugo, the plugin can run it through `uvx` instead (it
downloads Conjugo on first use):

```lua
opts = { cmd = { "uvx", "--from", "git+https://github.com/guilhermegarcia/conj", "conj" } }
```

![The Conjugo float in Neovim: "suis" under the cursor, with être's table and the other candidates](docs/nvim.svg)

With lazy.nvim:

```lua
{
  "guilhermegarcia/conj",
  cmd = "Conj",
  keys = { { "\\Lc", "<cmd>Conj<cr>", desc = "conjugate" } },
  opts = { default_lang = "fr" }, -- optional: its verbs listed first
}
```

`\Lc` puts it in a `\L` ("language") menu next to spell checking and a
dictionary, the way the author uses it. With which-key, `\L` pops up the
three options:

| Keys | Action |
|---|---|
| `\Ls` + `e`/`f`/`i`/`p` | toggle spell checking in English/French/Italian/Portuguese |
| `\Ld` + `e`/`f`/`i`/`p`/`g`/`s` | define the word under the cursor (…/German/Spanish) |
| `\Lc` | conjugate the word under the cursor (this plugin) |

Only `\Lc` comes with Conjugo; the other two are ordinary mappings in your own
config. A sketch, with a `def` dictionary command standing in for yours:

```lua
local names = { en = "English", fr = "French", it = "Italian", pt = "Portuguese",
                de = "German", es = "Spanish" }
require("which-key").add({
  { "\\L", group = "language" },
  { "\\Ls", group = "spellcheck" },
  { "\\Ld", group = "define" },
})
for key, lang in pairs({ e = "en", f = "fr", i = "it", p = "pt" }) do
  vim.keymap.set("n", "\\Ls" .. key, function()
    local on = vim.wo.spell and vim.bo.spelllang == lang
    vim.opt_local.spell = not on
    vim.opt_local.spelllang = { lang }
  end, { desc = names[lang] .. " spellcheck" })
end
for key, lang in pairs({ e = "en", f = "fr", i = "it", p = "pt", g = "de", s = "es" }) do
  vim.keymap.set("n", "\\Ld" .. key, function()
    vim.cmd("!def -l " .. lang .. " " .. vim.fn.shellescape(vim.fn.expand("<cword>")))
  end, { desc = "Define " .. names[lang] })
end
```

Spell checking and conjugation work together: when spell checking is on in
one language (`\Lsp`), `\Lc` lists that language's verbs first.

`:Conj fr` (or it/es/pt/en, or `b:conj_lang`) searches only that language.
Otherwise every language is searched, and a guessed language's verbs come
first: the spell-check language (when `'spell'` is on with a single
`'spelllang'`), else `default_lang` (`opts = { default_lang = "fr" }`).

When several verbs have the form (*suis*: *être*, *suivre*; *fui*: *fuir*,
*ser*, *ir*), the header lists them and `p`/`n` switch between them. In the
window, `q` or `Esc` closes it. Options, highlight groups: `:help conjugo`.

### Building the database yourself

From a clone, `uv run conj-build` builds `src/conj/data/conj.sqlite.gz` from
Wiktionary. It downloads about 250 MB of gzip-compressed Wiktextract dumps
(2.4 GB unpacked), caches them in `~/.cache/conj-build` (`--refresh` fetches
fresh copies), and builds the database in about 30 s. `conj` uses a local build
only once `DATA_TAG`/`DATA_SHA256` in `db.py` match it (`conj-build` prints the
checksum); until then, point `conj` at it with `CONJ_DB=/path/to/conj.sqlite`.

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
| `pronominal.py` | FR/ES/PT pronominals generated from the base verb |
| `search.py` | lookup: lemma, inflected form, fuzzy |
| `tui/` | Textual app |

To add a language, write `langs/xx.py` and add a source to `build.SOURCES`.
Any language with Wiktionary conjugation tables (German, Catalan…) can be
added this way.

## How it was made

Conjugo was built with [Claude Code](https://claude.com/claude-code),
Anthropic's coding agent. Guilherme D. Garcia designed the app and directed
the work: the languages and the open data sources, the linguistic decisions
(which tenses to show and how to label them, Brazilian clitic placement for
Portuguese), the interface and its keys, and the review of the output. Claude
Code wrote most of the code, the tests and the documentation, and investigated
the Wiktionary data. Commits made with it carry a `Co-Authored-By: Claude`
line.

## Credits

- Verb tables, auxiliaries and glosses: [Wiktionary](https://en.wiktionary.org)
  contributors, extracted by [Wiktextract](https://kaikki.org)
  (Tatu Ylonen, LREC 2022).
- Frequency ranking: [wordfreq](https://github.com/rspeer/wordfreq), by Robyn Speer.
- Interface: [Textual](https://textual.textualize.io); fuzzy search:
  [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz).

## License

The code is MIT (`LICENSE`), © 2026 Guilherme D. Garcia. The verb data is
CC BY-SA 4.0, from Wiktionary contributors via Wiktextract (`DATA_LICENSE.md`).
