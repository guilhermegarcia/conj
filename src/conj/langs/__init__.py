from .base import LangSpec
from .de import SPEC as DE
from .en import SPEC as EN
from .es import SPEC as ES
from .fr import SPEC as FR
from .it import SPEC as IT
from .ru import SPEC as RU
from .pt import SPEC as PT

LANGS: dict[str, LangSpec] = {spec.code: spec for spec in (FR, IT, EN, ES, PT, DE, RU)}

__all__ = ["LANGS", "LangSpec"]
