from .base import (
    COND_PRS, GER, IMP, IND_FUT, IND_IPFV, IND_PRS, IND_PST, INF, PTCP_PRS, PTCP_PST,
    SBJV_IPFV, SBJV_PRS, LangSpec, Section, compound,
)

# Compound tense -> auxiliary tense it is built on.
COMPOUNDS = {
    compound(IND_PRS): "Passé composé",
    compound(IND_IPFV): "Plus-que-parfait",
    compound(IND_PST): "Passé antérieur",
    compound(IND_FUT): "Futur antérieur",
    compound(COND_PRS): "Conditionnel passé",
    compound(SBJV_PRS): "Subjonctif passé",
    compound(SBJV_IPFV): "Subjonctif plus-que-parfait",
    compound(IMP): "Impératif passé",
    compound(INF): "Infinitif passé",
    compound(PTCP_PRS): "Participe passé composé",
}

SPEC = LangSpec(
    code="fr",
    name="Français",
    pronouns={"1s": "je", "2s": "tu", "3s": "il/elle", "1p": "nous", "2p": "vous", "3p": "ils/elles"},
    labels={
        IND_PRS: "Présent",
        IND_IPFV: "Imparfait",
        IND_PST: "Passé simple",
        IND_FUT: "Futur simple",
        COND_PRS: "Conditionnel présent",
        SBJV_PRS: "Subjonctif présent",
        SBJV_IPFV: "Subjonctif imparfait",
        IMP: "Impératif présent",
        INF: "Infinitif",
        PTCP_PRS: "Participe présent",
        PTCP_PST: "Participe passé",
        GER: "Gérondif",
        **COMPOUNDS,
    },
    sections=(
        Section("Indicatif", (
            IND_PRS, compound(IND_PRS), IND_IPFV, compound(IND_IPFV),
            IND_PST, compound(IND_PST), IND_FUT, compound(IND_FUT),
        )),
        Section("Conditionnel", (COND_PRS, compound(COND_PRS))),
        Section("Subjonctif", (SBJV_PRS, compound(SBJV_PRS), SBJV_IPFV, compound(SBJV_IPFV))),
        Section("Impératif", (IMP, compound(IMP))),
        Section("Formes nominales", (INF, compound(INF), PTCP_PRS, PTCP_PST, compound(PTCP_PRS), GER)),
    ),
    prefixes={SBJV_PRS: "que", SBJV_IPFV: "que", compound(SBJV_PRS): "que", compound(SBJV_IPFV): "que"},
    compound_keys=frozenset(COMPOUNDS),
)
