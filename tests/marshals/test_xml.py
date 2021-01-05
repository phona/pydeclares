from typing import Any, Optional, Type, TypeVar
from pydeclares import Declared, var
from pydeclares.marshals import xml
from xmlformatter import Formatter
from xml.etree import ElementTree as ET

_T = TypeVar("_T", bound=Any)
_xml_formatter = Formatter()


def format_xml(s: str):
    return _xml_formatter.format_string(s).decode()


def unmarshal(
    unmarshable: Type[_T], str_: str, options: Optional[xml.Options] = None
) -> _T:
    elem = ET.XML(str_)
    if options:
        return xml.unmarshal(unmarshable, elem, options)
    return xml.unmarshal(unmarshable, elem)


def marshal(marshable: Any, options: Optional[xml.Options] = None) -> str:
    if options:
        elem = xml.marshal(marshable, options)
    else:
        elem = xml.marshal(marshable)
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
