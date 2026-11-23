"""Golden tests against the built database (run `uv run python -m conj.build` first)."""

import pytest

from conj.compare import equivalents
from conj.compound import conjugate
from conj.db import DB
from conj.normalize import fold, it_orthography
from conj.search import resolve, search


@pytest.fixture(scope="session")
def db():
    return DB()


def cell(db, lang, lemma, tense, person=None, aux=None):
    hits = search(db, f"{lang}:{lemma}", limit=1)
    assert hits, lemma
    conj = conjugate(db, resolve(db, hits[0]), aux)
    for c in conj.tables[tense]:
        if c.person == person:
            return (c.pron + c.form).strip()
    raise KeyError((lemma, tense, person))


# ------------------------------------------------------------------ French
@pytest.mark.parametrize("lemma,tense,person,expected", [
    ("être", "IND.PRS", "1s", "je suis"),
    ("être", "IND.PST", "3p", "ils/elles furent"),
    ("être", "SBJV.PRS", "1p", "que nous soyons"),
    ("être", "PRF.IND.PRS", "1s", "j'ai été"),
    ("avoir", "IND.PRS", "1s", "j'ai"),
    ("avoir", "IND.FUT", "2p", "vous aurez"),
    ("aller", "IND.PRS", "3p", "ils/elles vont"),
    ("aller", "PRF.IND.PRS", "1s", "je suis allé(e)"),
    ("aller", "PRF.IND.PRS", "1p", "nous sommes allé(e)s"),
    ("aller", "SBJV.PRS", "3s", "qu'il/elle aille"),
    ("finir", "IND.PRS", "1p", "nous finissons"),
    ("finir", "SBJV.IPFV", "3s", "qu'il/elle finît"),
    ("se lever", "IND.PRS", "1s", "je me lève"),
    ("se lever", "PRF.IND.PRS", "3s", "il/elle s'est levé(e)"),
    ("se lever", "IMP", "2s", "lève-toi"),
    ("s'asseoir", "PRF.IND.PRS", "2s", "tu t'es assis(e)"),
    ("habiller", "IND.PRS", "1s", "j'habille"),
    ("s'en aller", "IND.PRS", "1s", "je m'en vais"),
    ("s'en aller", "PRF.IND.PRS", "1s", "je m'en suis allé(e)"),
    ("s'en aller", "PRF.IND.PRS", "1p", "nous nous en sommes allé(e)s"),
])
def test_french(db, lemma, tense, person, expected):
    assert cell(db, "fr", lemma, tense, person) == expected


def test_french_nonfinite(db):
    assert cell(db, "fr", "aller", "PRF.INF") == "être allé(e)(s)"
    assert cell(db, "fr", "parler", "GER") == "en parlant"
    assert cell(db, "fr", "se lever", "GER") == "en se levant"


# ------------------------------------------------------------------ Italian
@pytest.mark.parametrize("lemma,tense,person,expected,aux", [
    ("essere", "IND.PRS", "1s", "io sono", None),
    ("essere", "IND.PRS", "1p", "noi siamo", None),
    ("essere", "PRF.IND.PRS", "1s", "io sono stato/a", None),
    ("andare", "IND.PRS", "3p", "loro vanno", None),
    ("andare", "IND.FUT", "1s", "io andrò", None),
    ("andare", "PRF.IND.PRS", "1p", "noi siamo andati/e", None),
    ("venire", "IND.PRS", "1s", "io vengo", None),
    ("venire", "IND.PST", "3s", "lui/lei venne", None),
    ("correre", "PRF.IND.PRS", "1s", "io sono corso/a", "essere"),
    ("correre", "PRF.IND.PRS", "1s", "io ho corso", "avere"),
    ("alzarsi", "IND.PRS", "1s", "io mi alzo", None),
    ("alzarsi", "PRF.IND.PRS", "3s", "lui/lei si è alzato/a", None),
    ("andarsene", "PRF.IND.PRS", "3s", "lui/lei se n'è andato/a", None),
    ("dare", "IND.PRS", "3s", "lui/lei dà", None),
    ("finire", "IND.PRS", "1s", "io finisco", None),
    ("parlare", "IND.PST", "3s", "lui/lei parlò", None),
    ("parlare", "SBJV.PRS", "1p", "che noi parliamo", None),
])
def test_italian(db, lemma, tense, person, expected, aux):
    assert cell(db, "it", lemma, tense, person, aux) == expected


def test_italian_dual_auxiliary(db):
    verb = db.get("it", "correre")
    assert set(verb.aux) == {"essere", "avere"}


# ------------------------------------------------------------------ English
@pytest.mark.parametrize("lemma,tense,person,expected", [
    ("be", "IND.PRS", "1s", "I am"),
    ("be", "IND.PRS", "2s", "you are"),
    ("be", "IND.PST", "3s", "he/she/it was"),
    ("be", "SBJV.IPFV", "1s", "if I were"),
    ("go", "IND.PST", "1p", "we went"),
    ("go", "PRF.PRS", "3s", "he/she/it has gone"),
    ("go", "PROG.PRS", "1s", "I am going"),
    ("have", "IND.PRS", "3s", "he/she/it has"),
    ("walk", "PRF.PST", "3p", "they had walked"),
    ("walk", "FUT", "1s", "I will walk"),
    ("can", "IND.PST", "1s", "I could"),
])
def test_english(db, lemma, tense, person, expected):
    assert cell(db, "en", lemma, tense, person) == expected


def test_modals_have_no_periphrastic_tenses(db):
    conj = conjugate(db, db.get("en", "can"))
    assert "PRF.PRS" not in conj.tables and "IMP" not in conj.tables


# ------------------------------------------------------------------ lookup
@pytest.mark.parametrize("form,lang,lemma", [
    ("parlerions", "fr", "parler"),
    ("vengo", "it", "venire"),
    ("went", "en", "go"),
    ("fusse", "fr", "être"),
    ("parlo", "it", "parlare"),  # accent-insensitive: parlò
])
def test_reverse_lookup(db, form, lang, lemma):
    hits = search(db, form, lang)
    assert hits[0].lemma == lemma and hits[0].via in ("form", "lemma")


def test_fuzzy_and_prefix(db):
    assert search(db, "allr", "fr")[0].lemma == "aller"
    assert search(db, "se lev", "fr")[0].lemma == "se lever"


@pytest.mark.parametrize("lang,lemma,other,expected", [
    ("fr", "courir", "it", "correre"),
    ("en", "speak", "fr", "parler"),
    ("en", "speak", "it", "parlare"),
    ("fr", "savoir", "it", "sapere"),
    ("it", "volere", "fr", "vouloir"),
])
def test_equivalents(db, lang, lemma, other, expected):
    eq = equivalents(db, db.get(lang, lemma))
    assert expected in [v.lemma for v in eq[other][:3]]


# ------------------------------------------------------------------ normalization
@pytest.mark.parametrize("raw,std", [
    ("córro", "corro"), ("correrà", "correrà"), ("pàrla", "parla"), ("dà", "dà"),
    ("fà", "fa"), ("può", "può"), ("mi àlzo", "mi alzo"), ("correrèbbe", "correrebbe"),
])
def test_it_orthography(raw, std):
    assert it_orthography(raw) == std


def test_fold():
    assert fold("Parlò") == "parlo"
    assert fold("s’asseoir") == "s'asseoir"


# ------------------------------------------------------------------ TUI
def test_ctrl_q_quits_from_search_box(db):
    import asyncio

    from textual.widgets import Input

    from conj.tui.app import ConjApp

    async def run():
        app = ConjApp(db)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert isinstance(app.focused, Input)
            await pilot.press("q")  # typed, not a quit
            await pilot.pause()
            assert app.is_running
            assert app.query_one("#search", Input).value == "q"
            await pilot.press("ctrl+q")
            await pilot.pause()
            assert not app.is_running

    asyncio.run(run())
