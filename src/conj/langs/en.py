from .base import (
    IMP, IND_PRS, IND_PST, INF, PTCP_PRS, PTCP_PST, SBJV_IPFV, SBJV_PRS, LangSpec, Section,
)

# Periphrastic tenses, built in compound.py from be/have/will/would.
PROG_PRS = "PROG.PRS"
PROG_PST = "PROG.PST"
FUT = "FUT"
FUT_PROG = "FUT.PROG"
COND = "COND"
COND_PROG = "COND.PROG"
PRF_PRS = "PRF.PRS"
PRF_PST = "PRF.PST"
PRF_FUT = "PRF.FUT"
PRF_COND = "PRF.COND"
PRF_PROG_PRS = "PRF.PROG.PRS"
PRF_PROG_PST = "PRF.PROG.PST"
PRF_INF = "PRF.INF"

PERIPHRASTIC = {
    PROG_PRS: "Present continuous",
    PROG_PST: "Past continuous",
    FUT: "Future",
    FUT_PROG: "Future continuous",
    COND: "Conditional",
    COND_PROG: "Conditional continuous",
    PRF_PRS: "Present perfect",
    PRF_PST: "Past perfect",
    PRF_FUT: "Future perfect",
    PRF_COND: "Conditional perfect",
    PRF_PROG_PRS: "Present perfect continuous",
    PRF_PROG_PST: "Past perfect continuous",
    PRF_INF: "Perfect infinitive",
}

SPEC = LangSpec(
    code="en",
    name="English",
    pronouns={"1s": "I", "2s": "you", "3s": "he/she/it", "1p": "we", "2p": "you", "3p": "they"},
    labels={
        IND_PRS: "Simple present",
        IND_PST: "Simple past",
        SBJV_PRS: "Present subjunctive",
        SBJV_IPFV: "Past subjunctive",
        IMP: "Imperative",
        INF: "Infinitive",
        PTCP_PRS: "Present participle",
        PTCP_PST: "Past participle",
        **PERIPHRASTIC,
    },
    sections=(
        Section("Present", (IND_PRS, PROG_PRS, PRF_PRS, PRF_PROG_PRS)),
        Section("Past", (IND_PST, PROG_PST, PRF_PST, PRF_PROG_PST)),
        Section("Future", (FUT, FUT_PROG, PRF_FUT)),
        Section("Conditional", (COND, COND_PROG, PRF_COND)),
        Section("Subjunctive", (SBJV_PRS, SBJV_IPFV)),
        Section("Imperative", (IMP,)),
        Section("Non-finite", (INF, PRF_INF, PTCP_PRS, PTCP_PST)),
    ),
    prefixes={SBJV_PRS: "that", SBJV_IPFV: "if"},
    # Simple future/conditional stay visible: they are the only way to say them.
    compound_keys=frozenset(PERIPHRASTIC) - {FUT, COND},
    compare_keys=(IND_PRS, PRF_PRS, IND_PST, FUT, COND, SBJV_PRS),
)
