import unittest

from pydeclares import var, NamingStyle, Declared


class NamingStyleTestCase(unittest.TestCase):

	def test_snake_case(self):

		class Klass(Declared):
			test_var_a = var(int)

		struct = Klass(1)
		self.assertEqual(struct.to_dict(), {"test_var_a": 1})

		class Klass1(Declared):
			testVarB = var(int)

		struct = Klass1(1)
		self.assertEqual(struct.to_dict(), {"test_var_b": 1})

		class Klass3(Declared):
			TestVarD = var(int)

		struct = Klass3(1)
		self.assertEqual(struct.to_dict(), {"test_var_d": 1})

	def test_camel_case(self):

		class Klass(Declared):
			test_var_a = var(int, naming_style=NamingStyle.camelcase)

		struct = Klass(1)
		self.assertEqual(struct.to_dict(), {"testVarA": 1})

		class Klass1(Declared):
			testVarB = var(int, naming_style=NamingStyle.camelcase)

		struct = Klass(1)
		self.assertEqual(struct.to_dict(), {"testVarA": 1})

		class Klass3(Declared):
			TestVarD = var(int, naming_style=NamingStyle.camelcase)

		struct = Klass(1)
		self.assertEqual(struct.to_dict(), {"testVarA": 1})


class VarTestCase(unittest.TestCase):

	def test_post_init_case_1(self):

		class Klass(Declared):
			a = var(int)
			b = var(int)
			c = var(int, init=False)

			def __post_init__(self):
				self.c = self.a + self.b

		inst = Klass(1, 2)
		self.assertEqual(inst.a, 1)
		self.assertEqual(inst.b, 2)
		self.assertEqual(inst.c, 3)

	def test_post_init_case_2(self):

		class Klass(Declared):
			a = var(int)
			b = var(int)
			c = var(int, init=False)

			def __post_init__(self, c):
				self.c = c + 1

		inst = Klass(1, 2, 3)
		self.assertEqual(inst.a, 1)
		self.assertEqual(inst.b, 2)
		self.assertEqual(inst.c, 4)

	def test_post_init_case_3(self):

		class Klass(Declared):
			a = var(int)
			b = var(int)
			c = var(int, init=False, required=False)

			def __post_init__(self, c):
				self.c = c + 1

		inst = Klass(1, 2, 3)
		self.assertEqual(inst.a, 1)
		self.assertEqual(inst.b, 2)
		self.assertEqual(inst.c, 4)

	def test_post_init_case_4(self):

		class Klass(Declared):
			a = var(int)
			b = var(int)
			c = var(int, init=False, required=False)

			def __post_init__(self):
				self.c = self.a + self.b

		inst = Klass(1, 2)
		self.assertEqual(inst.a, 1)
		self.assertEqual(inst.b, 2)
		self.assertEqual(inst.c, 3)

	def test_default_params(self):

		class Klass(Declared):
			a = var(int)

		self.assertRaises(AttributeError, Klass)

		i1 = Klass(1)
		self.assertEqual(i1.a, 1)
		self.assertEqual(i1.to_json(), "{\"a\": 1}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{\"a\": 1}")

		i1 = Klass(None)
		self.assertEqual(i1.a, None)
		self.assertEqual(i1.to_json(), "{\"a\": null}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{}")

	def test_required(self):

		class Klass(Declared):
			a = var(int, required=False)

		i2 = Klass(1)
		self.assertEqual(i2.a, 1)
		self.assertEqual(i2.to_json(), "{\"a\": 1}")
		self.assertEqual(i2.to_json(skip_none_field=True), "{\"a\": 1}")

		i2 = Klass(None)
		self.assertEqual(i2.a, None)
		self.assertEqual(i2.to_json(), "{\"a\": null}")
		self.assertEqual(i2.to_json(skip_none_field=True), "{}")

	def test_ignore_serialize(self):

		class Klass(Declared):
			a = var(int, ignore_serialize=True)

		self.assertRaises(AttributeError, Klass)

		i3 = Klass(1)
		self.assertEqual(i3.a, 1)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

		i3 = Klass(None)
		self.assertEqual(i3.a, None)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

	def test_init(self):

		class Klass(Declared):
			a = var(int, init=False)

		i4 = Klass()
		self.assertEqual(i4.a, None)
		self.assertRaises(AttributeError, i4.to_json)
		i4.a = 1
		self.assertEqual(i4.a, 1)
		self.assertEqual(i4.to_json(), "{\"a\": 1}")
		self.assertEqual(i4.to_json(skip_none_field=True), "{\"a\": 1}")

		i4 = Klass(1)
		self.assertEqual(i4.a, None)
		self.assertRaises(AttributeError, i4.to_json)
		i4.a = 1
		self.assertEqual(i4.a, 1)
		self.assertEqual(i4.to_json(), "{\"a\": 1}")
		self.assertEqual(i4.to_json(skip_none_field=True), "{\"a\": 1}")

		i4 = Klass(None)
		self.assertEqual(i4.a, None)
		self.assertRaises(AttributeError, i4.to_json)
		self.assertRaises(AttributeError, i4.to_json, skip_none_field=True)

	def test_default(self):

		class Klass(Declared):
			a = var(int, default=10)

		i5 = Klass()
		self.assertEqual(i5.a, 10)
		self.assertEqual(i5.to_json(), "{\"a\": 10}")
		self.assertEqual(i5.to_json(skip_none_field=True), "{\"a\": 10}")

		i5 = Klass(1)
		self.assertEqual(i5.a, 1)
		self.assertEqual(i5.to_json(), "{\"a\": 1}")
		self.assertEqual(i5.to_json(skip_none_field=True), "{\"a\": 1}")

		i5 = Klass(None)
		self.assertEqual(i5.a, None)
		self.assertEqual(i5.to_json(), "{\"a\": null}")
		self.assertEqual(i5.to_json(skip_none_field=True), "{}")

	def test_default_factory(self):

		class Klass(Declared):
			a = var(int, default_factory=lambda: 10)

		i6 = Klass()
		self.assertEqual(i6.a, 10)
		self.assertEqual(i6.to_json(), "{\"a\": 10}")
		self.assertEqual(i6.to_json(skip_none_field=True), "{\"a\": 10}")

		i6 = Klass(1)
		self.assertEqual(i6.a, 1)
		self.assertEqual(i6.to_json(), "{\"a\": 1}")
		self.assertEqual(i6.to_json(skip_none_field=True), "{\"a\": 1}")

		i6 = Klass(None)
		self.assertEqual(i6.a, None)
		self.assertEqual(i6.to_json(), "{\"a\": null}")
		self.assertEqual(i6.to_json(skip_none_field=True), "{}")

	def test_field_name(self):

		class Klass(Declared):
			a = var(int, field_name="aa")

		self.assertRaises(AttributeError, Klass)

		i7 = Klass(1)
		self.assertEqual(i7.a, 1)
		self.assertEqual(i7.to_json(), "{\"aa\": 1}")
		self.assertEqual(i7.to_json(skip_none_field=True), "{\"aa\": 1}")

		i7 = Klass(None)
		self.assertEqual(i7.a, None)
		self.assertEqual(i7.to_json(), "{\"aa\": null}")
		self.assertEqual(i7.to_json(skip_none_field=True), "{}")


class ComplexVarTestCase(unittest.TestCase):

	def test_required_init(self):

		class Klass(Declared):
			a = var(int, required=False, init=False)

		i1 = Klass()
		self.assertEqual(i1.a, None)
		self.assertEqual(i1.to_json(), "{\"a\": null}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{}")

		i1 = Klass(1)
		self.assertEqual(i1.a, None)
		self.assertEqual(i1.to_json(), "{\"a\": null}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{}")

		i1 = Klass(1)
		i1.a = 10
		self.assertEqual(i1.a, 10)
		self.assertEqual(i1.to_json(), "{\"a\": 10}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{\"a\": 10}")

		i1 = Klass(None)
		self.assertEqual(i1.a, None)
		self.assertEqual(i1.to_json(), "{\"a\": null}")
		self.assertEqual(i1.to_json(skip_none_field=True), "{}")

	def test_required_ignore_serialize(self):

		class Klass(Declared):
			a = var(int, required=False, ignore_serialize=True)

		i2 = Klass(1)
		self.assertEqual(i2.a, 1)
		self.assertEqual(i2.to_json(), "{}")
		self.assertEqual(i2.to_json(skip_none_field=True), "{}")

		i2 = Klass(None)
		self.assertEqual(i2.a, None)
		self.assertEqual(i2.to_json(), "{}")
		self.assertEqual(i2.to_json(skip_none_field=True), "{}")

	def test_required_init_ignore_serialize(self):
		""""""

		class Klass(Declared):
			a = var(int, required=False, init=False, ignore_serialize=True)

		i3 = Klass()
		self.assertEqual(i3.a, None)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

		i3 = Klass()
		i3.a = 1
		self.assertEqual(i3.a, 1)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

		i3 = Klass(1)
		self.assertEqual(i3.a, None)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

		i3 = Klass(None)
		self.assertEqual(i3.a, None)
		self.assertEqual(i3.to_json(), "{}")
		self.assertEqual(i3.to_json(skip_none_field=True), "{}")

	def test_default_default_factory(self):
		""""""
		self.assertRaises(ValueError, var, int, default="aa", default_factory=lambda: 10)
