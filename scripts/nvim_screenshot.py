"""Draw the Conjugo Neovim float (dumped by nvim_screenshot.lua) as an SVG with Rich.

Regenerate docs/nvim.svg (needs tokyonight.nvim, here from lazy.nvim):

    TN=~/.local/share/nvim/lazy/tokyonight.nvim
    CONJ_SHOT_OUT=/tmp/dump.json nvim --headless -u NONE --cmd "set rtp+=.,$TN" \\
        -c "luafile scripts/nvim_screenshot.lua"
    uv run python scripts/nvim_screenshot.py /tmp/dump.json docs/nvim.svg
"""
import io
import json
import sys

from rich.console import Console
from rich.style import Style
from rich.text import Text

d = json.load(open(sys.argv[1]))
G = d["groups"]
cols, rows = d["cols"], d["rows"]


def style(group, **over):
    g = dict(G[group])
    g.update(over)
    return Style(color=g.get("fg"), bgcolor=g.get("bg"), bold=g.get("bold"), italic=g.get("italic"))


normal = style("Normal")
grid = [[(" ", normal) for _ in range(cols)] for _ in range(rows)]


def put(r, c, s, st):
    for i, ch in enumerate(s):
        if 0 <= r < rows and 0 <= c + i < cols:
            grid[r][c + i] = (ch, st)


# Editor window: relative line numbers like the user's setup, cursor line absolute.
cur = d["cursor"][0]
for r in range(rows - 2):
    if r < len(d["text"]):
        n = r + 1
        num = f"{n:>3} " if n == cur else f"{abs(n - cur):>3} "
        put(r, 0, num, style("CursorLineNr") if n == cur else style("LineNr"))
        put(r, 4, d["text"][r], normal)
    else:
        put(r, 0, "  ~", style("LineNr"))
put(rows - 2, 0, " " * cols, style("StatusLine"))
put(rows - 2, 0, " NORMAL  journal.md", style("StatusLine", bold=True))

# The float, border included.
f = d["float"]
fr, fc, fw, fh = f["row"], f["col"], f["width"], f["height"]
b, inner = style("FloatBorder"), style("NormalFloat")
put(fr, fc, "╭" + "─" * fw + "╮", b)
title = f["title"]
put(fr, fc + 1 + (fw - len(title)) // 2, title, style("FloatTitle"))
for i in range(fh):
    put(fr + 1 + i, fc, "│", b)
    put(fr + 1 + i, fc + 1, " " * fw, inner)
    put(fr + 1 + i, fc + 1 + fw, "│", b)
put(fr + fh + 1, fc, "╰" + "─" * fw + "╯", b)

# Buffer text with extmark highlights (byte columns -> character columns).
for i, line in enumerate(f["lines"]):
    raw = line.encode()
    put(fr + 1 + i, fc + 1, line[:fw], inner)
    for r, s, e, g in f["marks"]:
        if r != i:
            continue
        c0 = len(raw[:s].decode(errors="ignore"))
        seg = raw[s:e].decode(errors="ignore")
        base = G[g]
        st = style("NormalFloat")
        st = st + style(g) if base.get("bg") else st + Style(color=base.get("fg"), bold=base.get("bold"),
                                                             italic=base.get("italic"))
        put(fr + 1 + i, fc + 1 + c0, seg[: max(0, fw - c0)], st)

console = Console(record=True, width=cols, color_system="truecolor", file=io.StringIO(),
                  legacy_windows=False)
for row in grid:
    t = Text(no_wrap=True, overflow="crop")
    run, run_style = "", None
    for ch, st in row + [("", None)]:  # merge runs of one style: a much smaller SVG
        if st != run_style and run:
            t.append(run, run_style)
            run = ""
        run, run_style = run + ch, st

    console.print(t)
open(sys.argv[2], "w").write(console.export_svg(title="nvim · :Conj"))
