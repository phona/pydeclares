import unittest
from datetime import datetime
from enum import Enum
from typing import List

import pytest

from pydeclares import Declared, NamingStyle, var, vec
from pydeclares.exceptions import FieldRequiredError


class InnerJSONTestClass(Declared):
    ia = var(int)
    ib = var(int)


class BytesSerializer:
    def to_representation(self, bs: bytes) -> List:
        return list(bs)

    def to_internal_value(self, s: List) -> bytes:
        return bytes(s)


class ObjectCodec:
    def encode(self, o: object) -> object:
        return o

    def decode(self, o: object) -> object:
        return o


class JSONTestClass(Declared):
    a = var(int)
    b = var(float)
    c = var(bytes, serializer=BytesSerializer())
    d = var(str)
    e = var(bool)
    f = var(list)
    g = var(dict)


class CombineJSONTestClass(Declared):
    a = var(int)
    b = var(str)
    json = var(JSONTestClass)


class InheritedJSONTestClass(JSONTestClass, InnerJSONTestClass):
    iia = var(int)


class DatetimeCodec:
    def to_representation(self, dt: datetime) -> float:
        return dt.timestamp()

    def to_internal_value(self, timestamp: float):
        return datetime.fromtimestamp(timestamp)


class NewVarJsonTestClass(Declared):
    a = var(int, field_name="na")
    b = var(int, field_name="nb")
    c = var(datetime, serializer=DatetimeCodec())


class NewVarDeclaredTestCase(unittest.TestCase):
    def setUp(self):
        self.dt = datetime(2019, 10, 10, 10, 10, 10)
        self.timestamp = self.dt.timestamp()

    def test_str(self):
        json_obj = NewVarJsonTestClass(1, 2, self.dt)
        self.assertEqual(str(json_obj), "NewVarJsonTestClass(a=1, b=2, c=2019-10-10 10:10:10)")

    def test_to_dict(self):
        json_obj = NewVarJsonTestClass(1, 2, self.dt)
        self.assertEqual(json_obj.to_dict(), {"na": 1, "nb": 2, "c": self.dt})

    def test_to_json(self):
        json_obj = NewVarJsonTestClass(1, 2, self.dt)
        self.assertEqual(json_obj.to_json(), '{"na": 1, "nb": 2, "c": %0.1f}' % self.timestamp)

    def test_from_dict(self):
        dct = {"na": 1, "nb": 2, "c": self.dt}
        json_obj = NewVarJsonTestClass.from_dict(dct)
        self.assertEqual(str(json_obj), "NewVarJsonTestClass(a=1, b=2, c=2019-10-10 10:10:10)")

    def test_hash(self):
        dct_1 = {"na": 1, "nb": 2, "c": self.dt}
        dct_2 = {"na": 2, "nb": 1, "c": self.dt}
        json_obj_1 = NewVarJsonTestClass.from_dict(dct_1)
        json_obj_2 = NewVarJsonTestClass.from_dict(dct_1)
        json_obj_3 = NewVarJsonTestClass.from_dict(dct_2)
        self.assertEqual(hash(json_obj_1), hash(json_obj_2))
        self.assertNotEqual(hash(json_obj_1), hash(json_obj_3))

    def test_eq(self):
        dct_1 = {"na": 1, "nb": 2, "c": self.dt}
        dct_2 = {"na": 2, "nb": 1, "c": self.dt}
        json_obj_1 = NewVarJsonTestClass.from_dict(dct_1)
        json_obj_2 = NewVarJsonTestClass.from_dict(dct_1)
        json_obj_3 = NewVarJsonTestClass.from_dict(dct_2)
        self.assertNotEqual(json_obj_1, 1)
        self.assertEqual(json_obj_1, json_obj_2)
        self.assertNotEqual(json_obj_1, json_obj_3)


class CombineDeclaredTestCase(unittest.TestCase):
    def test_str(self):
        json_obj = CombineJSONTestClass(1, "123", JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}))
        self.assertEqual(
            str(json_obj),
            "CombineJSONTestClass(a=1, b=123, json=JSONTestClass("
            "a=1, b=1.2, c=b'123', d=123, e=True, f=[1, 2, 3], g={'a': 1}))",
        )

    def test_to_dict(self):
        json_obj = CombineJSONTestClass(1, "123", JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}))
        self.assertEqual(
            json_obj.to_dict(),
            {
                "a": 1,
                "b": "123",
                "json": {
                    "a": 1,
                    "b": 1.2,
                    "c": b"123",
                    "d": "123",
                    "e": True,
                    "f": [1, 2, 3],
                    "g": {"a": 1},
                },
            },
        )

    def test_to_json(self):
        json_obj = CombineJSONTestClass(1, "123", JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}))
        self.assertEqual(
            json_obj.to_json(),
            '{"a": 1, "b": "123", "json": {"a": 1, "b": 1.2, "c": [49, 50, 51], "d": "123"'
            ', "e": true, "f": [1, 2, 3], "g": {"a": 1}}}',
        )

    def test_from_dict(self):
        dct = {
            "a": 1,
            "b": "123",
            "json": {
                "a": 1,
                "b": 1.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        }
        json_obj = CombineJSONTestClass.from_dict(dct)
        self.assertEqual(
            str(json_obj),
            "CombineJSONTestClass(a=1, b=123, json=JSONTestClass("
            "a=1, b=1.2, c=b'123', d=123, e=True, f=[1, 2, 3], g={'a': 1}))",
        )

    def test_hash(self):
        dct_1 = {
            "a": 1,
            "b": "123",
            "json": {
                "a": 1,
                "b": 1.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        }
        dct_2 = {
            "a": 12,
            "b": "21123",
            "json": {
                "a": 1,
                "b": 2.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        }
        json_obj_1 = CombineJSONTestClass.from_dict(dct_1)
        json_obj_2 = CombineJSONTestClass.from_dict(dct_1)
        json_obj_3 = CombineJSONTestClass.from_dict(dct_2)
        self.assertEqual(hash(json_obj_1), hash(json_obj_2))
        self.assertNotEqual(hash(json_obj_1), hash(json_obj_3))

    def test_eq(self):
        dct_1 = {
            "a": 1,
            "b": "123",
            "json": {
                "a": 1,
                "b": 1.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        }
        dct_2 = {
            "a": 12,
            "b": "21123",
            "json": {
                "a": 1,
                "b": 2.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        }
        json_obj_1 = CombineJSONTestClass.from_dict(dct_1)
        json_obj_2 = CombineJSONTestClass.from_dict(dct_1)
        json_obj_3 = CombineJSONTestClass.from_dict(dct_2)
        self.assertNotEqual(json_obj_1, 1)
        self.assertEqual(json_obj_1, json_obj_2)
        self.assertNotEqual(json_obj_1, json_obj_3)


class InheritedDeclaredTestCase(unittest.TestCase):
    def test_str(self):
        json_obj = InheritedJSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}, 10, 11, 100)
        self.assertEqual(
            str(json_obj),
            "InheritedJSONTestClass(a=1, b=1.2, c=b'123', d=123, e=True, f=[1, 2, 3],"
            " g={'a': 1}, ia=10, ib=11, iia=100)",
        )

    def test_to_dict(self):
        json_obj = InheritedJSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}, 10, 11, 100)
        self.assertEqual(
            json_obj.to_dict(),
            {
                "iia": 100,
                "a": 1,
                "b": 1.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
                "ia": 10,
                "ib": 11,
            },
        )

    def test_to_json(self):
        json_obj = InheritedJSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1}, 10, 11, 100)
        self.assertEqual(
            json_obj.to_json(),
            '{"a": 1, "b": 1.2, "c": [49, 50, 51], "d": "123", "e": true, "f": [1, 2, 3],'
            ' "g": {"a": 1}, "ia": 10, "ib": 11, "iia": 100}',
        )

    def test_from_dict(self):
        dct = {
            "iia": 100,
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
            "ia": 10,
            "ib": 11,
        }
        json_obj = InheritedJSONTestClass.from_dict(dct)
        self.assertEqual(
            str(json_obj),
            "InheritedJSONTestClass(a=1, b=1.2, c=b'123', d=123, e=True,"
            " f=[1, 2, 3], g={'a': 1}, ia=10, ib=11, iia=100)",
        )

    def test_hash(self):
        dct_1 = {
            "iia": 100,
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
            "ia": 10,
            "ib": 11,
        }
        dct_2 = {
            "iia": 11,
            "a": 12,
            "b": 1.2,
            "c": b"123",
            "d": "1123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
            "ia": 10,
            "ib": 11,
        }
        json_obj_1 = InheritedJSONTestClass.from_dict(dct_1)
        json_obj_2 = InheritedJSONTestClass.from_dict(dct_1)
        json_obj_3 = InheritedJSONTestClass.from_dict(dct_2)
        self.assertEqual(hash(json_obj_1), hash(json_obj_2))
        self.assertNotEqual(hash(json_obj_1), hash(json_obj_3))

    def test_eq(self):
        dct_1 = {
            "iia": 100,
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
            "ia": 10,
            "ib": 11,
        }
        dct_2 = {
            "iia": 11,
            "a": 12,
            "b": 1.2,
            "c": b"123",
            "d": "1123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
            "ia": 10,
            "ib": 11,
        }
        json_obj_1 = InheritedJSONTestClass.from_dict(dct_1)
        json_obj_2 = InheritedJSONTestClass.from_dict(dct_1)
        json_obj_3 = InheritedJSONTestClass.from_dict(dct_2)
        self.assertNotEqual(json_obj_1, 1)
        self.assertEqual(json_obj_1, json_obj_2)
        self.assertNotEqual(json_obj_1, json_obj_3)


class SimpleDeclaredTestCase(unittest.TestCase):
    def test_str(self):
        json_obj = JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1})
        self.assertEqual(
            str(json_obj),
            "JSONTestClass(a=1, b=1.2, c=b'123', d=123, e=True, f=[1, 2, 3], g={'a': 1})",
        )

    def test_to_dict(self):
        class ITestJsonClass(Declared):
            a = var(int)
            b = var(int)
            c = var(int, required=False)

        json_obj = JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1})
        self.assertEqual(
            json_obj.to_dict(),
            {
                "a": 1,
                "b": 1.2,
                "c": b"123",
                "d": "123",
                "e": True,
                "f": [1, 2, 3],
                "g": {"a": 1},
            },
        )
        json_obj_1 = ITestJsonClass(a=1, b=1, c=2)
        self.assertRaises(FieldRequiredError, JSONTestClass, a=1, b=1.2, f=[1, 2, 3])
        self.assertEqual(json_obj_1.to_dict(skip_none_field=True), {"a": 1, "b": 1, "c": 2})
        self.assertEqual(json_obj_1.to_dict(), {"a": 1, "b": 1, "c": 2})

    def test_to_json(self):
        json_obj = JSONTestClass(1, 1.2, b"123", "123", True, [1, 2, 3], {"a": 1})
        self.assertEqual(
            json_obj.to_json(),
            '{"a": 1, "b": 1.2, "c": [49, 50, 51], "d": "123", "e": true, "f": [1, 2, 3], "g": {"a": 1}}',
        )

    def test_from_dict(self):
        dct = {
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
        }
        json_obj = JSONTestClass.from_dict(dct)
        self.assertEqual(
            str(json_obj),
            "JSONTestClass(a=1, b=1.2, c=b'123', d=123, e=True, f=[1, 2, 3], g={'a': 1})",
        )

    def test_hash(self):
        dct_1 = {
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
        }
        dct_2 = {
            "a": 2,
            "b": 1.2,
            "c": b"123",
            "d": "12333",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
        }
        json_obj_1 = JSONTestClass.from_dict(dct_1)
        json_obj_2 = JSONTestClass.from_dict(dct_1)
        json_obj_3 = JSONTestClass.from_dict(dct_2)
        self.assertEqual(hash(json_obj_1), hash(json_obj_2))
        self.assertNotEqual(hash(json_obj_1), hash(json_obj_3))

    def test_eq(self):
        dct_1 = {
            "a": 1,
            "b": 1.2,
            "c": b"123",
            "d": "123",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
        }
        dct_2 = {
            "a": 2,
            "b": 1.2,
            "c": b"123",
            "d": "12333",
            "e": True,
            "f": [1, 2, 3],
            "g": {"a": 1},
        }
        json_obj_1 = JSONTestClass.from_dict(dct_1)
        json_obj_2 = JSONTestClass.from_dict(dct_1)
        json_obj_3 = JSONTestClass.from_dict(dct_2)
        self.assertNotEqual(json_obj_1, 1)
        self.assertNotEqual(json_obj_1, json_obj_3)
        self.assertEqual(json_obj_1, json_obj_2)

    def test_empty(self):
        obj = JSONTestClass.empty()
        self.assertFalse(bool(obj))
        self.assertTrue(type(obj) is JSONTestClass)


class GenericListTestCase(unittest.TestCase):
    def test_v1_int(self):
        class Product(Declared):
            pay_types = vec(int)

        product = Product(pay_types=[0, 1])
        self.assertEqual(product.pay_types, [0, 1], product.pay_types)

        product = Product.from_dict({"pay_types": [0, 1]})
        self.assertEqual(product.pay_types, [0, 1], product.pay_types)

    def test_v2_int(self):
        class Test(Declared):
            picture_navi_ids = vec(int, naming_style=NamingStyle.camelcase)

        test = Test.from_dict({"pictureNaviIds": [0, 1]})
        self.assertEqual(test.picture_navi_ids, [0, 1])

    def test_v1_enum(self):
        class PayType(Enum):
            AliPay = 0
            WechatPay = 1

        class Product(Declared):
            pay_types = vec(PayType)

        product = Product(pay_types=[PayType.AliPay])
        self.assertEqual(product.pay_types, [PayType.AliPay])


def test_declared_dict_v1():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)

    s = Struct.from_dict({"p0": 1, "p1": "1"})
    assert s.p0 == 1
    assert s.p1 == "1"

    assert s.to_dict() == {"p0": 1, "p1": "1"}


def test_declared_dict_v1_castable_type():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(str)

    s = Struct.from_dict({"p0": "1", "p1": 1})
    assert s.to_dict() == {"p0": 1, "p1": "1"}


def test_declared_dict_v2():
    class Struct(Declared):
        p0 = vec(int)

    s = Struct.from_dict({"p0": [1, 2, 3]})
    assert s.p0 == [1, 2, 3]


def test_declared_dict_v2_castable_type():
    class Struct(Declared):
        p0 = vec(int)

    s = Struct.from_dict({"p0": [1, 2, 3]})
    assert s.p0 == [1, 2, 3]

    s = Struct.from_dict({"p0": ["1", "2", "3"]})
    assert s.p0 == [1, 2, 3]


def test_complex_fields():
    class Struct(Declared):
        p0 = var(bytes)
        p1 = var(complex)

    expect = Struct(b"123", complex(1, 1))
    assert Struct([49, 50, 51], 1 + 1j) == expect


def test_object_fields():
    class Struct(Declared):
        p0 = var(list)

    out = Struct([1, "3", 1.1])
    assert out.p0 == [1, "3", 1.1]


def test_inheritance():
    class Base(Declared):
        p0 = var(int)

    class Struct(Base):
        p1 = var(int)

    out = Struct(p0=1, p1=1)
    assert out.p0 == 1
    assert out.p1 == 1


def test_dict_v1():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(int)

    out = Struct(1, 1)
    assert out.to_dict() == {"p0": 1, "p1": 1}
    assert Struct.from_dict({"p0": 1, "p1": 1}) == out


def test_dict_v2():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(int)

    with pytest.raises(FieldRequiredError):
        Struct.from_dict({"p0": 1})


def test_dict_v3():
    class Struct(Declared):
        p0 = var(int)
        p1 = var(int, default=2)

    out = Struct.from_dict({"p0": 1})
    assert out.to_dict() == {"p0": 1, "p1": 2}
    assert out.to_dict() == {"p0": 1, "p1": 2}
