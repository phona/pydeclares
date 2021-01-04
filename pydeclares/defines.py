import re
from typing import Generic, TypeVar, Union

_T = TypeVar("_T")
Json = Union[dict, list, str, int, float, bool, None]
JsonData = Union[str, bytes, bytearray]


class Option(Generic[_T]):
    def __init__(self, val: Union[_T, "_MISSING_TYPE"]) -> None:
        self.val = val

    def __or__(self, other: _T):
        if self.val is MISSING or isinstance(self.val, _MISSING_TYPE):
            return other
        return self.val

    def take(self) -> _T:
        if self.val is MISSING or isinstance(self.val, _MISSING_TYPE):
            raise ValueError("can't take missing value")
        return self.val


class _MISSING_TYPE:
    def __str__(self):
        return "MISSING"


MISSING = _MISSING_TYPE()
CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>")


def issubtype(typ: type, supertype: type):
    try:
        supertype.__origin__
    except AttributeError:
        ...
