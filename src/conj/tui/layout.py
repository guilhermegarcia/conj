"""Keys typed on a non-Latin keyboard layout act as the Latin keys in the same place.

With a Cyrillic layout active no Latin binding would ever fire: j types й or о,
depending on the layout. Like vim's 'langmap', each such letter is read as the
Latin key at the same position, whenever the key is a command, not text (the
search box keeps what you type).

Layouts disagree (й is q on Russian ЙЦУКЕН, j on Russian – Phonetic), so on macOS
the table is built at startup from the layouts the user has enabled, by asking
macOS what each key produces (Carbon: TIS input sources + UCKeyTranslate). Only
letters of non-Latin scripts are mapped, so Latin layouts (and accented letters)
are never touched. Elsewhere, or if that fails, the standard ЙЦУКЕН table is used.
A layout that puts "." on the "/" key (Russian – PC) also gets "." -> "/" (search).

Kept in step with lexis/tui/layout.py.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import functools
import sys
import unicodedata

from textual import events
from textual.keys import _character_to_key

# Fallback: standard Russian ЙЦУКЕН on a US keyboard.
_RUSSIAN = "йцукенгшщзхъфывапролджэячсмитьбю" "ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ"
_LATIN = "qwertyuiop[]asdfghjkl;'zxcvbnm,." 'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>'
FALLBACK = dict(zip(_RUSSIAN, _LATIN))

# macOS virtual key codes of the US letter and punctuation keys.
_US_KEYS = {
    12: "q", 13: "w", 14: "e", 15: "r", 17: "t", 16: "y", 32: "u", 34: "i", 31: "o", 35: "p",
    33: "[", 30: "]", 0: "a", 1: "s", 2: "d", 3: "f", 5: "g", 4: "h", 38: "j", 40: "k", 37: "l",
    41: ";", 39: "'", 6: "z", 7: "x", 8: "c", 9: "v", 11: "b", 45: "n", 46: "m", 43: ",", 47: ".",
    44: "/", 50: "`", 42: "\\",
}
_SHIFTED = dict(zip("[];',./`\\", '{}:"<>?~|'))


def _non_latin_letter(ch: str) -> bool:
    try:
        return unicodedata.category(ch).startswith("L") and "LATIN" not in unicodedata.name(ch)
    except ValueError:
        return False


def _macos_tables() -> dict[str, str]:
    """{typed character: US key} for every enabled keyboard layout (macOS only)."""
    carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
    cf = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
    V = ctypes.c_void_p
    cf.CFArrayGetCount.restype, cf.CFArrayGetCount.argtypes = ctypes.c_long, [V]
    cf.CFArrayGetValueAtIndex.restype, cf.CFArrayGetValueAtIndex.argtypes = V, [V, ctypes.c_long]
    cf.CFDataGetBytePtr.restype, cf.CFDataGetBytePtr.argtypes = V, [V]
    cf.CFRelease.argtypes = [V]
    carbon.TISCreateInputSourceList.restype = V
    carbon.TISCreateInputSourceList.argtypes = [V, ctypes.c_bool]
    carbon.TISGetInputSourceProperty.restype = V
    carbon.TISGetInputSourceProperty.argtypes = [V, V]
    carbon.LMGetKbdType.restype = ctypes.c_uint8
    translate = carbon.UCKeyTranslate
    translate.argtypes = [V, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint32, ctypes.c_uint32,
                          ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.c_ulong,
                          ctypes.POINTER(ctypes.c_ulong), ctypes.c_wchar_p]
    layout_key = V.in_dll(carbon, "kTISPropertyUnicodeKeyLayoutData")
    kbd_type = carbon.LMGetKbdType()

    table: dict[str, str] = {}
    sources = carbon.TISCreateInputSourceList(None, False)  # enabled sources only
    try:
        for i in range(cf.CFArrayGetCount(sources)):
            data = carbon.TISGetInputSourceProperty(cf.CFArrayGetValueAtIndex(sources, i), layout_key)
            if not data:
                continue  # an input method, not a keyboard layout
            layout = cf.CFDataGetBytePtr(data)
            produced: dict[str, str] = {}
            for modifiers, shifted in ((0, False), (2, True)):  # 2 = shiftKey >> 8
                for code, us in _US_KEYS.items():
                    dead, length = ctypes.c_uint32(0), ctypes.c_ulong(0)
                    buf = ctypes.create_unicode_buffer(4)
                    translate(layout, code, 3, modifiers, kbd_type, 1,  # 3 = kUCKeyActionDisplay
                              ctypes.byref(dead), 4, ctypes.byref(length), buf)
                    ch = buf.value[: length.value]
                    if len(ch) == 1:
                        produced[ch] = (us.upper() if us.isalpha() else _SHIFTED[us]) if shifted else us
            for ch, us in produced.items():
                if _non_latin_letter(ch):
                    table.setdefault(ch, us)  # two layouts disagree: the first enabled wins
            if any(_non_latin_letter(ch) for ch in produced) and produced.get(".") == "/":
                table.setdefault(".", "/")
    finally:
        if sources:
            cf.CFRelease(sources)
    return table


@functools.cache
def table() -> dict[str, str]:
    if sys.platform == "darwin":
        try:
            found = _macos_tables()
            if found:
                return found
        except (OSError, AttributeError, ValueError):
            pass
    return dict(FALLBACK)


def latin(event: events.Key) -> events.Key | None:
    """The same key as a Latin keypress, or None if it needs no translation."""
    char = event.character
    latin_char = table().get(char) if char else None
    if latin_char is None:
        return None
    return events.Key(_character_to_key(latin_char), latin_char)
