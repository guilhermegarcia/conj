from .base import (
    COND_PRS, GER, IMP, IMP_NEG, IND_FUT, IND_IPFV, IND_PLPF, IND_PRS, IND_PST, INF, INF_PERS,
    PTCP_PST, SBJV_FUT, SBJV_IPFV, SBJV_PRS, LangSpec, Section, compound,
)

# Compound tenses, built on "ter" (Brazilian terminology).
COMPOUNDS = {
    compound(IND_PRS): "Pretérito perfeito composto",
    compound(IND_IPFV): "Mais-que-perfeito composto",
    compound(IND_FUT): "Futuro do presente composto",
    compound(COND_PRS): "Futuro do pretérito composto",
    compound(SBJV_PRS): "Pretérito perfeito (subj.)",
    compound(SBJV_IPFV): "Mais-que-perfeito (subj.)",
    compound(SBJV_FUT): "Futuro composto (subj.)",
    compound(INF): "Infinitivo impessoal composto",
    compound(INF_PERS): "Infinitivo pessoal composto",
    compound(GER): "Gerúndio composto",
}

SPEC = LangSpec(
    code="pt",
    name="Português",
    pronouns={"1s": "eu", "2s": "tu", "3s": "ele/ela/você", "1p": "nós", "2p": "vós",
              "3p": "eles/elas/vocês"},
    labels={
        IND_PRS: "Presente",
        IND_IPFV: "Pretérito imperfeito",
        IND_PST: "Pretérito perfeito",
        IND_PLPF: "Pretérito mais-que-perfeito",
        IND_FUT: "Futuro do presente",
        COND_PRS: "Futuro do pretérito",
        SBJV_PRS: "Presente do subjuntivo",
        SBJV_IPFV: "Imperfeito do subjuntivo",
        SBJV_FUT: "Futuro do subjuntivo",
        IMP: "Imperativo afirmativo",
        IMP_NEG: "Imperativo negativo",
        INF: "Infinitivo impessoal",
        INF_PERS: "Infinitivo pessoal",
        GER: "Gerúndio",
        PTCP_PST: "Particípio",
        **COMPOUNDS,
    },
    sections=(
        Section("Indicativo", (
            IND_PRS, compound(IND_PRS), IND_IPFV, compound(IND_IPFV), IND_PST, IND_PLPF,
            IND_FUT, compound(IND_FUT), COND_PRS, compound(COND_PRS),
        )),
        Section("Subjuntivo", (
            SBJV_PRS, compound(SBJV_PRS), SBJV_IPFV, compound(SBJV_IPFV),
            SBJV_FUT, compound(SBJV_FUT),
        )),
        Section("Imperativo", (IMP, IMP_NEG)),
        Section("Formas nominais", (
            INF, compound(INF), INF_PERS, compound(INF_PERS), GER, compound(GER), PTCP_PST,
        )),
    ),
    prefixes={
        SBJV_PRS: "que", compound(SBJV_PRS): "que",
        SBJV_IPFV: "se", compound(SBJV_IPFV): "se",
        SBJV_FUT: "quando", compound(SBJV_FUT): "quando",
    },
    compound_keys=frozenset(COMPOUNDS),
)
