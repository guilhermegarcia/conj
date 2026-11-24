from .base import (
    COND_PRS, GER, IMP, IMP_NEG, IND_FUT, IND_IPFV, IND_PRS, IND_PST, INF, PTCP_PST, SBJV_FUT,
    SBJV_IPFV, SBJV_PRS, LangSpec, Section, compound,
)

# Compound tenses, all built on "haber" (RAE terminology).
COMPOUNDS = {
    compound(IND_PRS): "Pretérito perfecto compuesto",
    compound(IND_IPFV): "Pretérito pluscuamperfecto",
    compound(IND_PST): "Pretérito anterior",
    compound(IND_FUT): "Futuro compuesto",
    compound(COND_PRS): "Condicional compuesto",
    compound(SBJV_PRS): "Pretérito perfecto (subj.)",
    compound(SBJV_IPFV): "Pluscuamperfecto (subj.)",
    compound(SBJV_FUT): "Futuro compuesto (subj.)",
    compound(INF): "Infinitivo compuesto",
    compound(GER): "Gerundio compuesto",
}

SPEC = LangSpec(
    code="es",
    name="Español",
    pronouns={"1s": "yo", "2s": "tú", "3s": "él/ella/usted", "1p": "nosotros",
              "2p": "vosotros", "3p": "ellos/ellas/ustedes"},
    labels={
        IND_PRS: "Presente",
        IND_IPFV: "Pretérito imperfecto",
        IND_PST: "Pretérito perfecto simple",
        IND_FUT: "Futuro",
        COND_PRS: "Condicional",
        SBJV_PRS: "Presente de subjuntivo",
        SBJV_IPFV: "Imperfecto de subjuntivo",
        SBJV_FUT: "Futuro de subjuntivo",
        IMP: "Imperativo afirmativo",
        IMP_NEG: "Imperativo negativo",
        INF: "Infinitivo",
        GER: "Gerundio",
        PTCP_PST: "Participio",
        **COMPOUNDS,
    },
    sections=(
        Section("Indicativo", (
            IND_PRS, compound(IND_PRS), IND_IPFV, compound(IND_IPFV),
            IND_PST, compound(IND_PST), IND_FUT, compound(IND_FUT),
        )),
        Section("Condicional", (COND_PRS, compound(COND_PRS))),
        Section("Subjuntivo", (
            SBJV_PRS, compound(SBJV_PRS), SBJV_IPFV, compound(SBJV_IPFV),
            SBJV_FUT, compound(SBJV_FUT),
        )),
        Section("Imperativo", (IMP, IMP_NEG)),
        Section("Formas no personales", (INF, compound(INF), GER, compound(GER), PTCP_PST)),
    ),
    prefixes={k: "que" for k in (SBJV_PRS, SBJV_IPFV, SBJV_FUT, compound(SBJV_PRS),
                                 compound(SBJV_IPFV), compound(SBJV_FUT))},
    compound_keys=frozenset(COMPOUNDS),
)
