from collections import UserList
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union, overload
from xml.etree import ElementTree as ET

from pydeclares import declares, variables
from pydeclares.defines import MISSING
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.utils import isinstance_safe, issubclass_safe
from typing_extensions import Protocol, runtime_checkable

_Literal = Union[str, int, float, bool, None]
_T = TypeVar("_T")
_DT = TypeVar("_DT", bound="declares.Declared")


class Vec(Generic[_T], UserList):
    data: List[_T]

    def __init__(self, tag, vec):
        # type: (str, variables.vec) -> None
        self.vec = vec
        self.tag = tag
        self.item_var = variables.compatible_var(
            vec.item_type, field_name=vec.field_name
        )
        self.data = []

    def marshal(self, options):
        # type: (Options) -> ET.Element
        root = ET.Element(self.tag)
        root.extend(marshal(item, options) for item in self)
        for item in self:
            root.append(marshal(item, options))
        return root

    def __str__(self):
        return str(self.data)


@runtime_checkable
class _Marshalable(Protocol):
    def marshal(self, options):
        # type: (Options) -> ET.Element
        ...


class Options:
    def __init__(self, skip_none_field=False, indent=None):
        # type: (bool, Optional[str]) -> None
        self.skip_none_field = skip_none_field
        self.indent = indent


_default_options = Options()


@overload
def unmarshal(marshalable, elem, options=...):
    # type: (Type[_DT], ET.Element, Options) -> _DT
    ...


@overload
def unmarshal(marshalable, elem, options=...):
    # type: (variables.vec[_T], ET.Element, Options) -> Vec[_T]
    ...


def unmarshal(marshalable, elem, options=_default_options):
    # type: (Union[variables.vec, Type[declares.Declared]], ET.Element, Options) -> Union[Vec, declares.Declared]
    if isinstance(marshalable, variables.vec):
        assert marshalable.field_name
        vec = Vec(elem.tag, marshalable)
        subs = elem.findall(marshalable.field_name)
        vec.extend(unmarshal(marshalable.item_type, sub, options) for sub in subs)
        return vec
    elif issubclass_safe(marshalable, declares.Declared):
        return _unmarshal_declared(marshalable, elem, options)

    raise MarshalError(f"type {marshalable} is not unmarshalable")


def _unmarshal_declared(typ, elem, options):
    # type: (Type[_DT], ET.Element, Options) -> _DT
    init_kwargs: Dict[str, Any] = {}
    for field in declares.fields(typ):
        if field.as_xml_attr:
            field_value = elem.get(field.field_name, MISSING)
        elif field.as_xml_text:
            field_value = elem.text
        elif isinstance(field, variables.vec):
            subs = elem.findall(field.field_name)
            field_value = [unmarshal(field.item_type, sub, options) for sub in subs]
        elif issubclass_safe(field.type_, declares.Declared):
            sub = elem.find(field.field_name)
            if sub is not None:
                field_value = unmarshal(field.type_, sub, options)
            else:
                field_value = MISSING
        else:
            field_value = getattr(elem.find(field.field_name), "text", MISSING)

        if field_value != MISSING:
            init_kwargs[field.name] = field_value

    return typ(**init_kwargs)


def marshal(marshalable_or_declared, options=_default_options):
    # type: (Union[_Marshalable, declares.Declared], Options) -> ET.Element
    if isinstance(marshalable_or_declared, declares.Declared):
        return _marshal_declared(marshalable_or_declared, options)
    else:
        return marshalable_or_declared.marshal(options)


def _marshal_declared(declared, options):
    # type: (declares.Declared, Options) -> ET.Element
    elem = ET.Element(
        declared.__xml_tag_name__
        if declared.__xml_tag_name__
        else declared.__class__.__name__.lower()
    )
    for field in declares.fields(declared):
        if field.as_xml_attr:
            attr = getattr(declared, field.name, MISSING)
            if attr is MISSING:
                continue
            elem.set(field.field_name, _marshal_text_field(field, attr))
        elif field.as_xml_text:
            text = getattr(declared, field.name, MISSING)
            if text is MISSING:
                continue
            elem.text = _marshal_text_field(field, text)
        elif isinstance_safe(field, variables.vec):
            li = getattr(declared, field.name, MISSING)
            if li is MISSING:
                continue

            elem.extend(_marshal_field(field, i, options) for i in li)
        else:
            val = getattr(declared, field.name, MISSING)
            if val is MISSING:
                continue
            elem.append(_marshal_field(field, val, options))

    return elem


def _marshal_text_field(field, value):
    # type: (variables.Var[Any, str], Any) -> str
    if isinstance(field.type_, _Literal.__args__):  # type: ignore
        return str(value)

    if not field.codec:
        raise MarshalError(
            f"can't marshal property {field.name} which are {field.type_!r}"
        )

    return field.codec.encode(value)


def _marshal_field(field, value, options):
    # type: (variables.Var, declares.Declared, Options) -> ET.Element
    if isinstance(value, declares.Declared):
        return marshal(value, options)
    else:
        text = _marshal_text_field(field, value)
        elem = ET.Element(field.field_name)
        elem.text = text
        return elem