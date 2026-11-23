"""Text normalization: search keys and Italian orthography."""

from __future__ import annotations

import re
import unicodedata

_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "‘": "'"})


def fold(text: str) -> str:
    """Accent- and case-insensitive search key ("Parlò" -> "parlo")."""
    text = unicodedata.normalize("NFD", text.translate(_APOSTROPHES).strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text)


_IT_VOWELS = "aeiouàèéìíòóùúîï"
_IT_VOWEL_GROUP = re.compile(f"[{_IT_VOWELS}]+")
_IT_ACCENTED = set("àèéìíòóùú")
# Monosyllables that keep a written accent in standard Italian spelling.
_IT_ACCENTED_MONOSYLLABLES = {"è", "dà", "può", "diè", "fé", "sé", "ché"}


def _strip_marks(token: str) -> str:
    nfd = unicodedata.normalize("NFD", token)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if not unicodedata.combining(c)))


def it_orthography(form: str) -> str:
    """Turn Wiktionary's stress-marked Italian into standard spelling.

    Wiktionary marks the stressed vowel of every word (córro, pàrla, correrà).
    Standard spelling writes an accent only on a final stressed vowel
    (correrà, parlò) and on a few monosyllables (è, dà, può).
    """
    out = []
    for token in form.split(" "):
        token = unicodedata.normalize("NFC", token)
        if not any(c in _IT_ACCENTED for c in token):
            out.append(token)
            continue
        if len(_IT_VOWEL_GROUP.findall(token)) <= 1:
            out.append(token if token in _IT_ACCENTED_MONOSYLLABLES else _strip_marks(token))
            continue
        last = token[-1]
        if last in _IT_ACCENTED:
            out.append(_strip_marks(token[:-1]) + last)
        else:
            out.append(_strip_marks(token))
    return " ".join(out)


_FR_VOWEL_START = re.compile(r"^[aeiouyàâäéèêëîïôöûùüœæh]", re.IGNORECASE)

# Verbs whose initial h is "aspiré" (no elision: je hais, il se hâte).
FR_H_ASPIRE = {
    "haïr", "hâter", "hurler", "heurter", "hanter", "harceler", "hisser", "hacher",
    "hausser", "héler", "hennir", "hérisser", "hocher", "huer", "hululer", "hasarder",
    "happer", "harasser", "harnacher", "haleter", "halter", "handicaper", "harponner",
    "hiérarchiser", "hiberner", "honnir", "houspiller", "hucher", "hurler", "hâler",
    "haler", "hacker", "hennir", "hanter", "hayer", "hérisser", "hongrer", "hoqueter",
}


def fr_elides(word: str, lemma: str | None = None) -> bool:
    """True if a French clitic (je, me, te, se, que) elides before `word`."""
    if not word or not _FR_VOWEL_START.match(word):
        return False
    if word[0] in "hH":
        base = (lemma or "").removeprefix("se ").removeprefix("s'")
        return base not in FR_H_ASPIRE
    return True
