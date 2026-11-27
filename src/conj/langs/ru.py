from .base import (
    GER, GER_PST, IMP, IND_FUT, IND_PRS, IND_PST, INF, PTCP_PASS_PRS, PTCP_PASS_PST, PTCP_PRS,
    PTCP_PST, LangSpec, Section,
)

# Built in compound.py: the past tense + бы (я говори́л(а) бы).
COND = "COND.BY"

ASPECT_NAMES = {"impf": "несовершенный вид", "pf": "совершенный вид", "both": "двувидовой"}
# What the partners of a verb of this aspect are called in the header.
PARTNER_NAMES = {"impf": "сов. вид", "pf": "несов. вид"}

SPEC = LangSpec(
    code="ru",
    name="Русский",
    pronouns={"1s": "я", "2s": "ты", "3s": "он/она/оно", "1p": "мы", "2p": "вы", "3p": "они"},
    labels={
        IND_PRS: "Настоящее время",
        IND_PST: "Прошедшее время",
        IND_FUT: "Будущее время",
        COND: "Сослагательное наклонение",
        IMP: "Повелительное наклонение",
        INF: "Инфинитив",
        PTCP_PRS: "Причастие действительное настоящего времени",
        PTCP_PST: "Причастие действительное прошедшего времени",
        PTCP_PASS_PRS: "Причастие страдательное настоящего времени",
        PTCP_PASS_PST: "Причастие страдательное прошедшего времени",
        GER: "Деепричастие настоящего времени",
        GER_PST: "Деепричастие прошедшего времени",
    },
    sections=(
        # Perfective verbs have no present tense: an empty table simply isn't shown.
        Section("Изъявительное наклонение", (IND_PRS, IND_PST, IND_FUT)),
        Section("Сослагательное наклонение", (COND,)),
        Section("Повелительное наклонение", (IMP,)),
        Section("Неличные формы", (
            INF, PTCP_PRS, PTCP_PST, PTCP_PASS_PRS, PTCP_PASS_PST, GER, GER_PST,
        )),
    ),
    # Nothing to hide: the future with буду is stored, the conditional is the only one.
    compound_keys=frozenset(),
)
