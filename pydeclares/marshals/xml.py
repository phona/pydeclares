from collections import UserList
from typing import Any, Generic, List, Optional, Type, TypeVar, Union
from xml.etree import ElementTree as ET
from xml.sax.handler import ContentHandler
from xml.sax.xmlreader import AttributesImpl

from pydeclares import declares, variables
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.utils import isinstance_safe, issubclass_safe
from typing_extensions import Protocol, runtime_checkable

_DT = TypeVar("_DT", bound="declares.Declared")
_T = TypeVar("_T")


@runtime_checkable
class _UnMarshalable(Protocol):
    def unmarshal(self, options: "Options") -> ET.Element:
        ...


@runtime_checkable
class _StructBuilder(Protocol):
    def tag(self) -> str:
        ...

    def build(self) -> Any:
        ...


class Options:
    def __init__(self, skip_none_field: bool = False, indent: Optional[str] = None):
        self.skip_none_field = skip_none_field
        self.indent = indent


class _DeferedListBuilder(Generic[_T]):
    def __init__(self, vec: "variables.vec[_T]") -> None:
        assert vec.field_name, "field name required if marshal a xml content"
        self.vec = vec
        self.data = []

    def tag(self):
        return self.vec.field_name

    def add(self, builder_or_val: Any):
        self.data.append(builder_or_val)

    def build(self) -> List[_T]:
        result = []
        for i in self.data:
            if isinstance(i, _StructBuilder):
                result.append(i.build())
            else:
                result.append(i)
        return result


class _DeferedBuilder(Generic[_DT]):
    def __init__(self, Struct: Type[_DT]) -> None:
        self.Struct = Struct
        self.fields = declares.fields(Struct)
        self.attrs = {}
        self.builders = {}

    def tag(self):
        return self.Struct.__xml_tag_name__ or self.Struct.__class__.__name__  # type: ignore

    def update_attrs(self, attrs: AttributesImpl):
        for field in filter(lambda f: f.as_xml_attr, self.fields):
            try:
                self.attrs[field.name] = attrs.getValue(field.field_name)
            except KeyError:
                ...

    def add_value(self, key: str, value: Any):
        self.attrs[key] = value

    def add_object(self, name: str, builder: _StructBuilder):
        self.builders[name] = builder

    def update_text(self, text: str):
        for field in filter(lambda f: f.as_xml_text, self.fields):
            self.attrs[field.name] = text

    def infer_type(self, field_name: str) -> type:
        for f in self.fields:
            if f.field_name == field_name:
                return f.type_
        raise KeyError(field_name)

    def build(self) -> _DT:
        attrs = {}
        attrs.update(self.attrs)
        attrs.update({k: v.build() for k, v in self.builders.items()})
        return self.Struct(**attrs)


class Parser(ContentHandler):
    def __init__(self, Struct: Type[declares.Declared]) -> None:
        super().__init__()
        self.Struct_stack = [_DeferedBuilder(Struct)]
        self.field_name = ""

    def startElement(self, name, attrs: AttributesImpl):
        current = self.Struct_stack[-1]
        if name == current.tag():
            current.update_attrs(attrs)
        self.field_name = name
        typ = current.infer_type(name)

    def characters(self, content):
        current = self.Struct_stack[-1]
        if self.field_name == current.tag():
            current.update_text(content)
        else:
            current.add_value(self.field_name, content)

    def endElement(self, name):
        if name == self.Struct_stack[-1].tag():
            self.Struct_stack.pop()

    def parse(self, source):
        ...


class Vec(Generic[_DT], UserList):
    data: List[_DT]

    def __init__(self, vec: "variables.vec"):
        self.vec = vec
        self.item_var = variables.compatible_var(vec.item_type)
        self.data = []

    def _marshal_item(self, item: _DT, options: "Options"):
        v = _marshal_field(self.vec.item_type, self.item_var, item, options)
        if not self.item_var.type_checking(v):
            return self.item_var.cast_it(v)  # type: ignore
        return v

    def unmarshal(self, options: "Options") -> str:
        return json.dumps(
            [_unmarshal_field(self.vec.item_type, self.vec, i, options) for i in self]
        )

    def __str__(self):
        return str(self.data)


def marshal(typ, elem: ET.Element, options: Options, tag_name: Optional[str] = None):
    if isinstance(typ, variables.vec):
        assert tag_name
        ...

    return _marshal(typ, elem, options)


def _marshal(marshalable, elem: ET.Element, options: Options):
    if isinstance_safe(marshalable, variables.vec):
        ...
    elif issubclass_safe(marshalable, declares.Declared):
        ...

    raise MarshalError(f"type {marshalable} is not marshalable")


def unmarshal(
    unmarshalable_or_declared: Union[_UnMarshalable, "declares.Declared"],
    options: Options,
) -> ET.Element:
    ...
