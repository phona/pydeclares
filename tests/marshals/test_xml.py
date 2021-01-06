from typing import Any, Optional, Type, TypeVar
from xml.etree import ElementTree as ET

import pytest
from xmlformatter import Formatter

from pydeclares import Declared, var
from pydeclares.exceptions import FieldRequiredError
from pydeclares.marshals import xml

_T = TypeVar("_T", bound=Any)
_xml_formatter = Formatter()


def format_xml(s: str):
    return _xml_formatter.format_string(s).decode()


def unmarshal(unmarshalable: Type[_T], str_: str, options: Optional[xml.Options] = None) -> _T:
    elem = ET.XML(str_)
    if options:
        return xml.unmarshal(unmarshalable, elem, options)
    return xml.unmarshal(unmarshalable, elem)


def marshal(marshalable: Any, options: Optional[xml.Options] = None) -> str:
    if options:
        elem = xml.marshal(marshalable, options)
    else:
        elem = xml.marshal(marshalable)
    return ET.tostring(elem).decode()


def test_unmarshal_xml_literal_v1():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(int, as_xml_attr=True)
        p1 = var(str)
        p2 = var(float)

    _str = '<root p0="1"><p1>string</p1><p2>1.1</p2></root>'
    out = unmarshal(Struct, _str)
    assert out.p0 == 1
    assert out.p1 == "string"
    assert out.p2 == 1.1
    assert marshal(out) == _str


def test_unmarshal_xml_literal_v2():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(int, as_xml_attr=True)
        p1 = var(str, required=False)
        p2 = var(float)

    _str = '<root p0="1"><p2>1.1</p2></root>'
    out = unmarshal(Struct, _str)
    assert out.p0 == 1
    assert out.p1 is None
    assert out.p2 == 1.1
    assert marshal(out) == '<root p0="1"><p1 /><p2>1.1</p2></root>'


def test_unmarshal_xml_literal_v3():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(int, as_xml_attr=True)
        p1 = var(str, required=False)
        p2 = var(float)

    _str = '<root p0="1"><p2>1.1</p2></root>'
    out = unmarshal(Struct, _str)
    assert out.p0 == 1
    assert out.p1 is None
    assert out.p2 == 1.1
    assert marshal(out, xml.Options(True)) == '<root p0="1"><p2>1.1</p2></root>'


def test_unmarshal_xml_literal_v4():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(int, as_xml_attr=True, required=False)
        p1 = var(str)
        p2 = var(float)

    _str = '<root p0=""><p1>string</p1><p2>1.1</p2></root>'
    out = unmarshal(Struct, _str)
    assert out.p0 is None
    assert out.p1 == "string"
    assert out.p2 == 1.1
    assert marshal(out) == '<root p0=""><p1>string</p1><p2>1.1</p2></root>'


def test_unmarshal_xml_literal_v5():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(int, as_xml_attr=True, required=False)
        p1 = var(str)
        p2 = var(float)

    _str = '<root p0=""><p1>string</p1><p2>1.1</p2></root>'
    out = unmarshal(Struct, _str)
    assert out.p0 is None
    assert out.p1 == "string"
    assert out.p2 == 1.1
    assert marshal(out, xml.Options(True)) == '<root><p1>string</p1><p2>1.1</p2></root>'


def test_unmarshal_xml_text_v1():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, as_xml_text=True)

    _str = '<root>string</root>'
    out = unmarshal(Struct, _str)
    assert out.p0 == "string"
    assert marshal(out, xml.Options(True)) == _str


def test_unmarshal_xml_text_v2():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, as_xml_text=True)

    _str = '<root></root>'

    with pytest.raises(FieldRequiredError):
        unmarshal(Struct, _str)


def test_unmarshal_xml_text_v3():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, as_xml_text=True, required=False)

    _str = '<root></root>'

    out = unmarshal(Struct, _str)
    assert out.p0 is None
    assert marshal(out) == "<root />"


def test_unmarshal_xml_ignore_serialize():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, ignore_serialize=True)

    _str = '<root><p0>hello</p0></root>'

    out = unmarshal(Struct, _str)
    assert out.p0 == "hello"
    assert marshal(out) == "<root />"


def test_unmarshal_xml_skip_none_field():
    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, required=False)

    _str = '<root><p0>hello</p0></root>'

    out = unmarshal(Struct, _str)
    assert out.p0 == "hello"
    out.p0 = None
    assert marshal(out, xml.Options(True)) == "<root />"


def test_unmarshal_xml_seiralize_text():
    class S:
        def to_representation(self, s: str):
            return s[::-1]

        def to_internal_value(self, s: str):
            return s[::-1]

    class Struct(Declared):
        __xml_tag_name__ = "root"

        p0 = var(str, as_xml_text=True, serializer=S())

    _str = "<root>hello</root>"
    out = unmarshal(Struct, _str)
    assert out.p0 == 'olleh'
    assert marshal(out) == _str
