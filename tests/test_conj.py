"""Golden tests against the built database (run `uv run python -m conj.build` first)."""

import pytest

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


# ------------------------------------------------------------------ Spanish
@pytest.mark.parametrize("lemma,tense,person,expected", [
    ("ser", "IND.PRS", "1s", "yo soy"),
    ("ser", "IND.PST", "3s", "él/ella/usted fue"),
    ("ir", "IND.PRS", "3p", "ellos/ellas/ustedes van"),
    ("hablar", "IND.PRS", "2s", "tú hablas"),  # tagged "informal": must not be dropped
    ("hablar", "PRF.IND.PRS", "1s", "yo he hablado"),
    ("hablar", "SBJV.IPFV", "1s", "que yo hablara / hablase"),
    ("hablar", "IMP", "3s", "(usted) hable"),
    ("hablar", "IMP.NEG", "2s", "no hables"),
    ("tener", "IND.PRS", "1s", "yo tengo"),
    ("quejarse", "IND.PRS", "1s", "yo me quejo"),
    ("quejarse", "PRF.IND.PRS", "3s", "él/ella/usted se ha quejado"),
    ("quejarse", "IMP.NEG", "2s", "no te quejes"),
])
def test_spanish(db, lemma, tense, person, expected):
    assert cell(db, "es", lemma, tense, person) == expected


def test_spanish_nonfinite(db):
    assert cell(db, "es", "hablar", "PTCP.PST") == "hablado"  # not the four gendered forms
    assert cell(db, "es", "quejarse", "GER") == "quejándose"
    assert cell(db, "es", "quejarse", "PRF.GER") == "habiéndose quejado"
    assert cell(db, "es", "quejarse", "PRF.INF") == "haberse quejado"


# ------------------------------------------------------------------ Portuguese
@pytest.mark.parametrize("lemma,tense,person,expected", [
    ("ser", "IND.PRS", "1s", "eu sou"),
    ("falar", "IND.PST", "3s", "ele/ela/você falou"),
    ("falar", "IND.PLPF", "1s", "eu falara"),
    ("falar", "PRF.IND.PRS", "1s", "eu tenho falado"),
    ("falar", "SBJV.IPFV", "1p", "se nós falássemos"),
    ("falar", "SBJV.FUT", "1s", "quando eu falar"),
    ("falar", "PRF.SBJV.FUT", "3p", "quando eles/elas/vocês tiverem falado"),
    ("falar", "INF.PERS", "2s", "tu falares"),
    ("falar", "IMP.NEG", "2s", "não fales"),
    ("pôr", "IND.PRS", "1s", "eu ponho"),
])
def test_portuguese(db, lemma, tense, person, expected):
    assert cell(db, "pt", lemma, tense, person) == expected


def test_portuguese_nonfinite(db):
    assert cell(db, "pt", "falar", "PTCP.PST") == "falado"
    assert cell(db, "pt", "falar", "PRF.GER") == "tendo falado"


def test_accent_marks_the_form(db):
    """hablé (preterite) must not also match hable (subjunctive)."""
    conj = conjugate(db, db.get("es", "hablar"))
    assert conj.find("hablé") == [("IND.PST", "1s")]


def test_no_ipa_in_forms(db):
    conj = conjugate(db, db.get("fr", "parler"))
    assert all("ʁ" not in c.form for c in conj.tables["IND.PRS"])


# ------------------------------------------------------------------ lookup
@pytest.mark.parametrize("form,lang,lemma", [
    ("parlerions", "fr", "parler"),
    ("vengo", "it", "venire"),
    ("went", "en", "go"),
    ("fusse", "fr", "être"),
    ("parlo", "it", "parlare"),  # accent-insensitive: parlò
    ("hablé", "es", "hablar"),
    ("falássemos", "pt", "falar"),
    ("ponho", "pt", "pôr"),
])
def test_reverse_lookup(db, form, lang, lemma):
    hits = search(db, form, lang)
    assert hits[0].lemma == lemma and hits[0].via in ("form", "lemma")


def test_fuzzy_and_prefix(db):
    assert search(db, "allr", "fr")[0].lemma == "aller"
    assert search(db, "se lev", "fr")[0].lemma == "se lever"


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


def test_escape_leaves_search_box_then_q_quits(db):
    import asyncio

    from textual.widgets import Input

    from conj.tui.app import ConjApp

    async def run():
        app = ConjApp(db)
        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("p", "a", "r", "l", "e", "r")
            await pilot.pause(0.3)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.focused, Input)
            await pilot.press("escape")  # a second Esc stays out of the search box
            await pilot.pause()
            assert not isinstance(app.focused, Input)
            await pilot.press("q")
            await pilot.pause()
            assert not app.is_running

    asyncio.run(run())


# ------------------------------------------------------------------ first-run download
def _fake_release(tmp_path):
    import gzip
    import hashlib
    import sqlite3

    raw = tmp_path / "src.sqlite"
    sqlite3.connect(raw).execute("CREATE TABLE t(x)").connection.commit()
    gz = tmp_path / "conj.sqlite.gz"
    gz.write_bytes(gzip.compress(raw.read_bytes()))
    return gz.as_uri(), hashlib.sha256(gz.read_bytes()).hexdigest()


def test_downloads_database_when_none_is_packaged(tmp_path, monkeypatch):
    from conj import db as dbmod

    url, sha = _fake_release(tmp_path)
    monkeypatch.delenv("CONJ_DB", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CONJ_DB_URL", url)
    monkeypatch.setattr(dbmod, "PACKAGED", tmp_path / "missing.sqlite.gz")
    monkeypatch.setattr(dbmod, "DATA_SHA256", sha)
    path = dbmod.db_path()
    assert path == tmp_path / "cache" / "conj" / f"conj-{dbmod.DATA_TAG}.sqlite"
    assert path.read_bytes().startswith(b"SQLite format 3")
    assert [p.name for p in path.parent.iterdir()] == [path.name]  # no leftover .gz/.part
    assert dbmod.db_path() == path  # second run: no download


def test_download_rejects_bad_checksum(tmp_path, monkeypatch):
    from conj import db as dbmod

    url, _ = _fake_release(tmp_path)
    monkeypatch.delenv("CONJ_DB", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CONJ_DB_URL", url)
    monkeypatch.setattr(dbmod, "PACKAGED", tmp_path / "missing.sqlite.gz")
    monkeypatch.setattr(dbmod, "DATA_SHA256", "0" * 64)
    with pytest.raises(FileNotFoundError, match="checksum mismatch"):
        dbmod.db_path()
    assert not list((tmp_path / "cache" / "conj").iterdir())


def test_glosses_skip_alternative_form_senses(db):
    """estudar has an Internet-euphemism sense "alternative form of estuprar": not a meaning."""
    assert db.get("pt", "estudar").glosses == ["to study"]
    # ...but an entry with nothing else keeps its pointer.
    assert "realize" in db.get("en", "realise").glosses[0]


def _isolated(tmp_path, monkeypatch, packaged, sha, url):
    from conj import db as dbmod

    monkeypatch.delenv("CONJ_DB", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CONJ_DB_URL", url)
    monkeypatch.setattr(dbmod, "PACKAGED", packaged)
    monkeypatch.setattr(dbmod, "DATA_SHA256", sha)
    return dbmod


def test_packaged_copy_of_the_pinned_release_is_used(tmp_path, monkeypatch):
    url, sha = _fake_release(tmp_path)
    packaged = tmp_path / "conj.sqlite.gz"  # the release file itself
    dbmod = _isolated(tmp_path, monkeypatch, packaged, sha, (tmp_path / "nowhere.gz").as_uri())
    assert dbmod.db_path().name == f"conj-{dbmod.DATA_TAG}.sqlite"  # no download attempted


def test_stale_packaged_copy_is_ignored(tmp_path, monkeypatch, capsys):
    import gzip

    url, sha = _fake_release(tmp_path)
    stale = tmp_path / "stale.sqlite.gz"
    stale.write_bytes(gzip.compress(b"an older release"))
    dbmod = _isolated(tmp_path, monkeypatch, stale, sha, url)
    path = dbmod.db_path()
    assert path.read_bytes().startswith(b"SQLite format 3")  # the downloaded release
    assert "ignoring it" in capsys.readouterr().err


# ------------------------------------------------------------------ generated ES/PT pronominals
@pytest.mark.parametrize("lang,lemma,tense,person,expected", [
    ("es", "levantarse", "IND.PRS", "1s", "yo me levanto"),
    ("es", "levantarse", "PRF.IND.PRS", "3s", "él/ella/usted se ha levantado"),
    ("es", "levantarse", "IMP", "2s", "levántate"),
    ("es", "levantarse", "IMP", "1p", "levantémonos"),
    ("es", "levantarse", "IMP", "2p", "levantaos"),
    ("es", "levantarse", "IMP.NEG", "2s", "no te levantes"),
    ("es", "vestirse", "IMP", "2p", "vestíos"),
    ("es", "irse", "IMP", "2p", "idos"),
    ("es", "reírse", "IND.PRS", "1s", "yo me río"),  # Wiktionary's own table says "me reo"
    ("pt", "levantar-se", "IND.PRS", "1s", "eu me levanto"),
    ("pt", "levantar-se", "PRF.IND.PRS", "1s", "eu tenho me levantado"),
    ("pt", "levantar-se", "IMP", "3s", "(você) levante-se"),
    ("pt", "levantar-se", "IMP", "1p", "levantemo-nos"),
    ("pt", "levantar-se", "IMP.NEG", "2s", "não te levantes"),
    ("pt", "levantar-se", "INF.PERS", "1p", "nós nos levantarmos"),
])
def test_generated_iberian_pronominals(db, lang, lemma, tense, person, expected):
    assert cell(db, lang, lemma, tense, person) == expected


def test_generated_iberian_nonfinite(db):
    assert cell(db, "es", "levantarse", "GER") == "levantándose"
    assert cell(db, "es", "levantarse", "PRF.GER") == "habiéndose levantado"
    assert cell(db, "pt", "levantar-se", "INF") == "levantar-se"
    assert cell(db, "pt", "levantar-se", "PRF.INF") == "ter-se levantado"


@pytest.mark.parametrize("form,clitic,drop,expected", [
    ("levanta", "te", 0, "levántate"), ("pon", "te", 0, "ponte"), ("vamos", "nos", 1, "vámonos"),
    ("vestid", "os", 1, "vestíos"), ("levantando", "se", 0, "levantándose"),
    ("levantar", "se", 0, "levantarse"), ("ríe", "te", 0, "ríete"),
])
def test_spanish_enclitic_stress(form, clitic, drop, expected):
    from conj.pronominal import es_enclitic
    assert es_enclitic(form, clitic, drop) == expected


def test_search_offers_generated_pronominals(db):
    assert search(db, "levantarse", "es")[0].lemma == "levantarse"
    assert search(db, "levantar-se")[0].lemma == "levantar-se"
    assert search(db, "levantarse", "pt")[0].lemma == "levantar-se"  # hyphen optional with pt


@pytest.mark.parametrize("left,right", [("h", "l"), ("left", "right")])
def test_h_l_switch_panes_and_j_follows_focus(db, left, right):
    import asyncio

    from textual.widgets import OptionList

    from conj.tui.app import ConjApp

    async def run():
        app = ConjApp(db, query="parl")
        async with app.run_test() as pilot:
            await pilot.pause(0.4)
            await pilot.press("escape")  # leave the search box: paradigm has focus
            await pilot.pause()
            results = app.query_one("#results", OptionList)
            await pilot.press(left)
            await pilot.pause()
            assert app.focused is results
            first = app.current
            await pilot.press("j")
            await pilot.pause()
            assert results.highlighted == 1 and app.current != first  # paradigm follows the list
            await pilot.press(right)
            await pilot.pause()
            assert app.focused is app.query_one("#main")

    asyncio.run(run())


def test_digits_switch_language_even_while_typing(db):
    import asyncio

    from textual.widgets import Input

    from conj.tui.app import ConjApp

    async def run():
        app = ConjApp(db)
        async with app.run_test() as pilot:
            await pilot.press("p", "a", "r", "l", "4")
            await pilot.pause(0.3)
            assert app.lang == "pt"
            assert app.query_one("#search", Input).value == "parl"  # the digit was not typed
            await pilot.press("escape", "6")
            await pilot.pause()
            assert app.lang is None

    asyncio.run(run())


def test_question_mark_toggles_home_page(db):
    import asyncio

    from conj.tui.app import ConjApp

    async def run():
        app = ConjApp(db, query="parler")
        async with app.run_test() as pilot:
            await pilot.pause(0.4)
            await pilot.press("escape")
            welcome, paradigm = app.query_one("#welcome"), app.query_one("#paradigm")
            assert paradigm.display and not welcome.display
            await pilot.press("question_mark")
            await pilot.pause()
            assert welcome.display and not paradigm.display
            await pilot.press("question_mark")
            await pilot.pause()
            assert paradigm.display and not welcome.display

    asyncio.run(run())
