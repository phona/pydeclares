import copy
import unittest
from enum import Enum
from datetime import date, datetime

from pydeclares import Declared, var, as_codec
from pydeclares.codecs import _CODECS


class CodecsTestCase(unittest.TestCase):
    def setUp(self):
        self._codecs = copy.deepcopy(_CODECS)

    def tearDown(self):
        _CODECS.update(self._codecs)

    def test_date(self):
        class Klass(Declared):
            d = var(date, default=date.today())

        @as_codec(date)
        class DateCodec:
            @classmethod
            def encode(cls, o):
                return o.isoformat()

        klass = Klass(date(2019, 10, 8))
        self.assertEqual(klass.to_json(), "{\"d\": \"2019-10-08\"}")

    def test_datetime(self):
        class Klass(Declared):
            d = var(datetime, default=datetime.now())

        @as_codec(datetime)
        class DateCodec:
            fmt = "%Y-%m-%d %H:%M:%S"

            @classmethod
            def encode(cls, o):
                return o.strftime(cls.fmt)

            @classmethod
            def decode(cls, o):
                return datetime.strptime(o, cls.fmt)

        klass1 = Klass(datetime(2019, 10, 8, 17, 14, 10))
        klass2 = Klass.from_json("{\"d\": \"2019-10-08 17:14:10\"}")
        self.assertEqual(klass1, klass2)

    def test_enum(self):
        class YesNo(Enum):
            n = "0"
            y = "1"

        class Klass(Declared):
            acquired = var(YesNo)

        klass = Klass(YesNo.y)
        self.assertEqual(klass.to_json(), "{\"acquired\": \"1\"}")

    def test_custom_default_codec(self):
        class CustomDate(date):
            """"""

        class Klass(Declared):
            d = var(date, default=date.today())
            sd = var(CustomDate, default=CustomDate.today())

        @as_codec(date)
        class DateCodec:
            @classmethod
            def encode(cls, o):
                return o.isoformat()

            @classmethod
            def decode(cls, o):
                return CustomDate(2019, 10, 8)

        @as_codec(CustomDate)
        class CustomDateCodec:
            @classmethod
            def encode(cls, o):
                return o.isoformat() + "p"

            @classmethod
            def decode(cls, o):
                return CustomDate(2019, 10, 7)

        klass = Klass(date(2019, 10, 8), CustomDate(2019, 10, 7))
        json_string = "{\"d\": \"2019-10-08\", \"sd\": \"2019-10-07p\"}"
        self.assertEqual(klass.to_json(), json_string)
        self.assertEqual(Klass.from_json(json_string), klass)
