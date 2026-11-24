from .base import LangSpec
from .en import SPEC as EN
from .es import SPEC as ES
from .fr import SPEC as FR
from .it import SPEC as IT
from .pt import SPEC as PT

LANGS: dict[str, LangSpec] = {spec.code: spec for spec in (FR, IT, EN, ES, PT)}

__all__ = ["LANGS", "LangSpec"]
