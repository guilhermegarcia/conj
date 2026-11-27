"""Link to Lexis (`lexis`): define the current verb from Conjugo.

The two apps are separate `uv tool` installs, so they talk through their
commands, never imports. `D` runs `lexis` in the same terminal while the TUI
is suspended; quitting Lexis comes back here.

Each app tells the other which verb it came from (LEXIS_FROM_CONJ /
CONJ_FROM_LEXIS = "lang:lemma"). Asking to go back to that same verb exits
instead of opening a third app on top: Lexis → C → conj → D returns to Lexis.
"""

from __future__ import annotations

import os
import shutil
import subprocess

FROM_LEXIS = "CONJ_FROM_LEXIS"  # set by Lexis when it opens conj
TO_LEXIS = "LEXIS_FROM_CONJ"    # set here when conj opens Lexis


def lexis_command() -> str | None:
    return shutil.which("lexis")


def came_from(lang: str, lemma: str) -> bool:
    """True when this conj was opened by Lexis on this very verb."""
    return os.environ.get(FROM_LEXIS) == f"{lang}:{lemma}"


def run_lexis(lang: str, lemma: str) -> None:
    """Run Lexis on `lemma`, limited to `lang` dictionaries. Blocks until Lexis quits."""
    exe = lexis_command()
    if exe:
        subprocess.run([exe, "--lang", lang, lemma],
                       env={**os.environ, TO_LEXIS: f"{lang}:{lemma}"}, check=False)
