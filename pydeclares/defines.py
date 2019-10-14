import re
from typing import Any, Dict, Type, Union


class _MISSING_TYPE:
    def __str__(self):
        return "MISSING"


MISSING = _MISSING_TYPE()
CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>")
Json: Type[Any] = Union[dict, list, str, int, float, bool, None]
JsonData = Union[str, bytes, bytearray]

_REGISTER_DECLARED_CLASS: Dict[str, type] = {}
