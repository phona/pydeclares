from collections import UserList
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, overload
from xml.etree import ElementTree as ET

from pydeclares import declares, variables
from pydeclares.defines import MISSING
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.typing import Protocol, runtime_checkable
from pydeclares.utils import isinstance_safe, issubclass_safe

_Literal = Union[str, int, float, bool, None]
_T = TypeVar("_T")
_DT = TypeVar("_DT", bound="declares.Declared")


class Vec(List[_T], UserList):
    def __init__(self, tag, vec):
        # type: (str, variables.vec) -> None
        self.vec = vec
        self.tag = tag
        self.item_var = variables.compatible_var(vec.item_type, field_name=vec.field_name)

    def marshal(self, options):
        # type: (Options) -> ET.Element
        root = ET.Element(self.tag)
        root.extend(marshal(item, options) for item in self)  # type: ignore
        return root


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
    field_value: Any
    for field in declares.fields(typ):
        if field.as_xml_attr:
            field_value = elem.get(field.field_name, MISSING)
            if field_value is None or field_value == "":
                field_value = MISSING
        elif field.as_xml_text:
            field_value = elem.text
            if field_value is None or field_value == "":
                field_value = MISSING
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
            if field_value is None:
                field_value = MISSING

        if field_value != MISSING:
            if field.serializer:
                field_value = field.serializer.to_internal_value(field_value)
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
    elem = ET.Element(declared.__xml_tag_name__ if declared.__xml_tag_name__ else declared.__class__.__name__.lower())
    for field in declares.fields(declared):
        if field.ignore_serialize:
            continue

        if field.as_xml_attr:
            attr = getattr(declared, field.name)
            if attr is None:
                if options.skip_none_field:
                    continue

                attr = ""

            elem.set(field.field_name, _marshal_text_field(field, attr))
        elif field.as_xml_text:
            text = getattr(declared, field.name)
            if text is None:
                if options.skip_none_field:
                    continue

                text = ""

            elem.text = _marshal_text_field(field, text)
        elif isinstance_safe(field, variables.vec):
            li = getattr(declared, field.name)
            elem.extend(_marshal_field(field, i, options) for i in li)
        else:
            val = getattr(declared, field.name)
            if val is None:
                if not options.skip_none_field:
                    sub = ET.Element(field.field_name)
                    elem.append(sub)
            else:
                elem.append(_marshal_field(field, val, options))

    return elem


def _marshal_text_field(field, value):
    # type: (variables.Var[Any, str], Any) -> str
    if field.serializer:
        return field.serializer.to_representation(value)

    if issubclass(field.type_, _Literal.__args__):  # type: ignore
        return str(value)

    raise MarshalError(f"can't marshal property `{field.name}` which are `{field.type_!r}`")


def _marshal_field(field, value, options):
    # type: (variables.Var, declares.Declared, Options) -> ET.Element
    if isinstance(value, declares.Declared):
        return _marshal_declared(value, options)
    else:
        text = _marshal_text_field(field, value)
        elem = ET.Element(field.field_name)
        elem.text = text
        return elem
