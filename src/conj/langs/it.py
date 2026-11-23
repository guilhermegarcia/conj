from .base import (
    COND_PRS, GER, IMP, IND_FUT, IND_IPFV, IND_PRS, IND_PST, INF, PTCP_PRS, PTCP_PST,
    SBJV_IPFV, SBJV_PRS, LangSpec, Section, compound,
)

COMPOUNDS = {
    compound(IND_PRS): "Passato prossimo",
    compound(IND_IPFV): "Trapassato prossimo",
    compound(IND_PST): "Trapassato remoto",
    compound(IND_FUT): "Futuro anteriore",
    compound(COND_PRS): "Condizionale passato",
    compound(SBJV_PRS): "Congiuntivo passato",
    compound(SBJV_IPFV): "Congiuntivo trapassato",
    compound(INF): "Infinito passato",
    compound(GER): "Gerundio passato",
}

SPEC = LangSpec(
    code="it",
    name="Italiano",
    pronouns={"1s": "io", "2s": "tu", "3s": "lui/lei", "1p": "noi", "2p": "voi", "3p": "loro"},
    labels={
        IND_PRS: "Presente",
        IND_IPFV: "Imperfetto",
        IND_PST: "Passato remoto",
        IND_FUT: "Futuro semplice",
        COND_PRS: "Condizionale presente",
        SBJV_PRS: "Congiuntivo presente",
        SBJV_IPFV: "Congiuntivo imperfetto",
        IMP: "Imperativo",
        INF: "Infinito",
        GER: "Gerundio",
        PTCP_PRS: "Participio presente",
        PTCP_PST: "Participio passato",
        **COMPOUNDS,
    },
    sections=(
        Section("Indicativo", (
            IND_PRS, compound(IND_PRS), IND_IPFV, compound(IND_IPFV),
            IND_PST, compound(IND_PST), IND_FUT, compound(IND_FUT),
        )),
        Section("Condizionale", (COND_PRS, compound(COND_PRS))),
        Section("Congiuntivo", (SBJV_PRS, compound(SBJV_PRS), SBJV_IPFV, compound(SBJV_IPFV))),
        Section("Imperativo", (IMP,)),
        Section("Modi indefiniti", (INF, compound(INF), GER, compound(GER), PTCP_PRS, PTCP_PST)),
    ),
    prefixes={SBJV_PRS: "che", SBJV_IPFV: "che", compound(SBJV_PRS): "che", compound(SBJV_IPFV): "che"},
    compound_keys=frozenset(COMPOUNDS),
    compare_keys=(IND_PRS, compound(IND_PRS), IND_IPFV, IND_FUT, COND_PRS, SBJV_PRS),
)
