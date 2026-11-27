"""Keys typed on a Cyrillic keyboard layout act as the Latin keys in the same place.

With the Russian (ЙЦУКЕН) layout active, j is о, k is л, G is П: no Latin binding
would ever fire. Like vim's 'langmap', each Cyrillic letter is read as the Latin
key at the same position on a US keyboard, whenever the key is a command, not text.
Typed text (the search box) is left alone.

The Russian layout also puts "." where "/" is, so "." means "/" (search); "." is
not a command in either app. Kept in step with lexis/tui/layout.py.
"""

from __future__ import annotations

from textual import events
from textual.keys import _character_to_key

_RUSSIAN = "йцукенгшщзхъфывапролджэячсмитьбю" "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ"
_LATIN = "qwertyuiop[]asdfghjkl;'zxcvbnm,." 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>'
LATIN_AT = dict(zip(_RUSSIAN, _LATIN)) | {".": "/"}


def latin(event: events.Key) -> events.Key | None:
    """The same key as a Latin keypress, or None if it needs no translation."""
    char = event.character
    if not char or char not in LATIN_AT:
        return None
    latin_char = LATIN_AT[char]
    return events.Key(_character_to_key(latin_char), latin_char)
