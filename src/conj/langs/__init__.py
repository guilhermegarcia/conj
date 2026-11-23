from .base import LangSpec
from .en import SPEC as EN
from .fr import SPEC as FR
from .it import SPEC as IT

LANGS: dict[str, LangSpec] = {spec.code: spec for spec in (FR, IT, EN)}

__all__ = ["LANGS", "LangSpec"]
