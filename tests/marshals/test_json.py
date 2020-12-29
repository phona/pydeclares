from pydeclares import var, Declared
from pydeclares.variables import vec, kv
from pydeclares.marshals import json


def test_marshal_literal():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)
        p2 = var(float)
        p3 = var(bool)
        p4 = var(type(None))

    _str = '{"p0": 1, "p1": "1", "p2": 1.1, "p3": false, "p4": null}'
    out = json.marshal(Struct, _str, json.Options())
    assert out.p0 == 1
    assert out.p1 == "1"

    assert json.unmarshal(out, json.Options()) == _str


def test_marshal_literal_not_matched_type():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(float)

    _str = '{"p0": 1.1, "p1": 1}'
    out = json.marshal(Struct, _str, json.Options())
    assert out.p0 == 1
    assert out.p1 == 1.0

    assert json.unmarshal(out, json.Options()) == '{"p0": 1, "p1": 1.0}'


def test_marshal_vec():
    v = vec(int)
    _str = "[0, 1, 2, 3]"
    out = json.marshal(v, _str, json.Options())
    assert out == [0, 1, 2, 3]
    assert json.unmarshal(out, json.Options()) == _str


def test_marshal_vec_not_matched_type():
    v = vec(int)
    _str = "[0, 1.1, 2.1, 3.1]"
    out = json.marshal(v, _str, json.Options())
    assert out == [0, 1, 2, 3]
    assert json.unmarshal(out, json.Options()) == "[0, 1, 2, 3]"
