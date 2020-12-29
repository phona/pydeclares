import re
from typing import (
    Any,
    Callable,
    Collection, Dict,
    Generic, List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from typing_extensions import Protocol
from xml.etree import ElementTree as ET

_T = TypeVar("_T")
_Self = TypeVar("_Self", bound="Serializable")
Json = Union[Dict[str, "Json"], List["Json"], str, int, float, bool, None]
JsonData = Union[str, bytes, bytearray]


class Serializable(Protocol):
    @classmethod
    def from_json(
        cls: Type[_Self],
        s: "JsonData",
        *,
        parse_float: Optional[Callable[[str], Any]] = None,
        parse_int: Optional[Callable[[str], Any]] = None,
        parse_constant: Optional[Callable[[str], Any]] = None,
        **kw: Any,
    ) -> _Self:
        ...

    def to_json(
        self,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: Optional[Union[int, str]] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable[[Any], "Json"]] = None,
        sort_keys: bool = False,
        skip_none_field: bool = False,
        **kw: Any,
    ) -> str:
        ...

    @classmethod
    def from_xml(cls: Type[_Self], element: ET.Element) -> _Self:
        ...

    def to_xml(
        self,
        tag: Optional[str] = None,
        skip_none_field: bool = False,
        indent: Optional[str] = None,
    ) -> ET.Element:
        ...

    @classmethod
    def from_collection(cls: Type[_Self], collection: Collection[_T]) -> _Self:
        ...

    def to_collection(self) -> Collection[_T]:
        ...


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
