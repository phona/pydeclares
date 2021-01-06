from datetime import datetime
from enum import Enum
from typing import Any, Optional, Type, TypeVar

import pytest

from pydeclares import Declared, var
from pydeclares.exceptions import FieldRequiredError
from pydeclares.marshals import json
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.variables import kv, vec

_T = TypeVar("_T", bound=Any)


def unmarshal(unmarshalable: Type[_T], str_: str, options: Optional[json.Options] = None) -> _T:
    if options:
        return json.unmarshal(unmarshalable, str_, json.Options())
    else:
        return json.unmarshal(unmarshalable, str_)


def marshal(marshalable: Any, options: Optional[json.Options] = None) -> str:
    if options:
        return json.marshal(marshalable, options)
    else:
        return json.marshal(marshalable)


def test_marshal_literal_v1():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)
        p2 = var(float)
        p3 = var(bool)

    _str = '{"p0": 1, "p1": "1", "p2": 1.1, "p3": false}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out.p0 == 1
    assert out.p1 == "1"

    assert json.marshal(out, json.Options()) == _str


def test_marshal_literal_v2():
    class Inner(Declared):
        p0 = var(int)
        p1 = var(str)
        p2 = var(float)
        p3 = var(bool)

    class Struct(Declared):
        p0 = var(Inner, required=False)

    _str = '{"p0": null}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out.p0 is None

    assert json.marshal(out, json.Options()) == _str


def test_marshal_literal_not_matched_type():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(float)

    _str = '{"p0": 1.1, "p1": 1}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out.p0 == 1
    assert out.p1 == 1.0

    assert json.marshal(out, json.Options()) == '{"p0": 1, "p1": 1.0}'


def test_marshal_composition():
    class Inner(Declared):
        p0 = var(int)
        p1 = var(str)

    class Struct(Declared):
        p0 = var(Inner)

    _str = '{"p0": {"p0": 1, "p1": "hello"}}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out.p0 == Inner(p0=1, p1="hello")
    assert json.marshal(out, json.Options()) == _str


def test_marshal_inheritance():
    class Inner(Declared):
        p0 = var(int)
        p1 = var(str)

    class Struct(Inner):
        p2 = var(int)

    _str = '{"p0": 0, "p1": "1", "p2": 2}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out.p0 == 0
    assert out.p1 == "1"
    assert out.p2 == 2
    assert json.marshal(out, json.Options()) == _str


def test_marshal_vec():
    v = vec(int)
    _str = "[0, 1, 2, 3]"
    out = json.unmarshal(v, _str, json.Options())
    assert out == [0, 1, 2, 3]
    assert json.marshal(out, json.Options()) == _str


def test_marshal_vec_not_matched_type():
    v = vec(int)
    _str = "[0, 1.1, 2.1, 3.1]"
    out = json.unmarshal(v, _str, json.Options())
    assert out == [0, 1, 2, 3]
    assert json.marshal(out, json.Options()) == "[0, 1, 2, 3]"


def test_marsharl_vec_composition():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)

    v = vec(Struct)
    _str = '[{"p0": 1, "p1": "1"}, {"p0": 2, "p1": "2"}]'
    out = json.unmarshal(v, _str, json.Options())
    assert out == [Struct(1, "1"), Struct(2, "2")]
    assert json.marshal(out, json.Options()) == _str


def test_marshal_kv():
    v = kv(str, int)
    _str = '{"a": 1, "b": 2}'
    out = json.unmarshal(v, _str, json.Options())
    assert out == {"a": 1, "b": 2}
    assert json.marshal(out, json.Options()) == _str


def test_marshal_kv_not_matched_type():
    v = kv(str, int)
    _str = '{"a": "1", "b": "2"}'
    out = json.unmarshal(v, _str, json.Options())
    assert out == {"a": 1, "b": 2}
    assert json.marshal(out, json.Options()) == '{"a": 1, "b": 2}'


def test_marshal_kv_composition():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)

    v = kv(str, Struct)
    _str = '{"a": {"p0": 1, "p1": "1"}, "b": {"p0": 2, "p1": "2"}}'
    out = json.unmarshal(v, _str, json.Options())
    assert out == {"a": Struct(1, "1"), "b": Struct(2, "2")}
    assert json.marshal(out, json.Options()) == _str


def test_marshal_compose_vec_v1():
    class Struct(Declared):
        p0 = vec(int)

    _str = '{"p0": [1, 2, 3]}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out == Struct([1, 2, 3])
    assert json.marshal(out, options=json.Options()) == _str


def test_marshal_compose_vec_v2():
    class Struct(Declared):
        p0 = vec(int, required=False)

    _str = '{"p0": null}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out == Struct()
    assert json.marshal(out, options=json.Options()) == _str


def test_marshal_compositions():
    class Inner(Declared):
        p0 = vec(int)
        p1 = kv(str, int)

    class Struct(Declared):
        p0 = vec(int)
        p1 = kv(str, int)
        p2 = var(Inner)

    _str = '{"p0": [1, 2], "p1": {"a": 1}, "p2": {"p0": [1, 2], "p1": {"a": 1}}}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out == Struct(p0=[1, 2], p1={"a": 1}, p2=Inner(p0=[1, 2], p1={"a": 1}))
    assert json.marshal(out, json.Options()) == _str


def test_marshal_enum():
    class Fruit(Enum):
        Apple = 0
        Banana = 1

    class FruitSerializer:
        def to_representation(self, fruit: Fruit) -> int:
            return fruit.value

        def to_internal_value(self, val: int) -> Fruit:
            return Fruit(val)

    class Struct(Declared):
        p0 = var(Fruit, serializer=FruitSerializer())

    _str = '{"p0": 0}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out == Struct(p0=Fruit.Apple)
    assert json.marshal(out, json.Options()) == _str


def test_marshal_kv_compositions():
    class Struct(Declared):
        p0 = kv(str, int, required=False)

    _str = '{"p0": null}'
    out = json.unmarshal(Struct, _str, json.Options())
    assert out == Struct()
    assert json.marshal(out, json.Options()) == _str


def test_unmarshal_generic_list():
    Li = var(list)
    _str = '[1, "2", 3.1]'
    li = unmarshal(Li, _str)  # type: ignore
    assert li == [1, "2", 3.1]
    assert marshal(li) == _str


def test_unmarshal_generic_dict():
    Di = var(dict)
    _str = '{"a": 1, "b": "1", "c": 1.1}'
    di = unmarshal(Di, _str)  # type: ignore
    assert di == {"a": 1, "b": "1", "c": 1.1}
    assert marshal(di) == _str


def test_unmarshal_not_required():
    class Struct(Declared):
        p0 = var(int, required=False)

    out = unmarshal(Struct, "{}")
    assert out.p0 is None


def test_unmarshal_empty_create():
    class Struct(Declared):
        p0 = var(int)

    with pytest.raises(FieldRequiredError):
        unmarshal(Struct, "{}")


def test_unmarshal_default():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(int, default=1)

    out = unmarshal(Struct, '{"p0": 1}')
    assert out.p1 == 1


def test_umarshal_not_json_value():
    class Struct(Declared):
        p0 = var(datetime)

    out = Struct(datetime.now())
    with pytest.raises(MarshalError):
        marshal(out)
