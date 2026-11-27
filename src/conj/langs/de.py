from .base import (
    IMP, IND_PRS, IND_PST, INF, INF_ZU, PTCP_PRS, PTCP_PST, SBJV_IPFV, SBJV_PRS, LangSpec,
    Section, compound,
)

# Tenses built in compound.py: with the auxiliary (haben / sein) + Partizip II, or with
# werden. Präteritum is IND.PST; Konjunktiv I and II are SBJV.PRS and SBJV.IPFV.
FUT1 = "FUT.I"         # werde gehen
FUT2 = "FUT.II"        # werde gegangen sein
WUERDE = "COND.WUERDE"  # würde gehen

COMPOUNDS = {
    compound(IND_PRS): "Perfekt",
    compound(IND_PST): "Plusquamperfekt",
    compound(SBJV_PRS): "Konjunktiv I Perfekt",
    compound(SBJV_IPFV): "Konjunktiv II Plusquamperfekt",
    compound(INF): "Infinitiv Perfekt",
}
WERDEN = {
    FUT1: "Futur I",
    FUT2: "Futur II",
    WUERDE: "würde-Form",
}

SPEC = LangSpec(
    code="de",
    name="Deutsch",
    pronouns={"1s": "ich", "2s": "du", "3s": "er/sie/es", "1p": "wir", "2p": "ihr", "3p": "sie/Sie"},
    labels={
        IND_PRS: "Präsens",
        IND_PST: "Präteritum",
        SBJV_PRS: "Konjunktiv I",
        SBJV_IPFV: "Konjunktiv II",
        IMP: "Imperativ",
        INF: "Infinitiv",
        INF_ZU: "zu-Infinitiv",
        PTCP_PRS: "Partizip I",
        PTCP_PST: "Partizip II",
        **COMPOUNDS,
        **WERDEN,
    },
    sections=(
        Section("Indikativ", (
            IND_PRS, compound(IND_PRS), IND_PST, compound(IND_PST), FUT1, FUT2,
        )),
        Section("Konjunktiv", (
            SBJV_PRS, compound(SBJV_PRS), SBJV_IPFV, compound(SBJV_IPFV), WUERDE,
        )),
        Section("Imperativ", (IMP,)),
        Section("Infinite Formen", (INF, INF_ZU, compound(INF), PTCP_PRS, PTCP_PST)),
    ),
    # Futur I and the würde-form stay visible with compounds hidden: like English
    # will / would, they are the everyday way to say these things.
    compound_keys=frozenset(COMPOUNDS) | {FUT2},
)
