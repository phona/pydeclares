import re
import unittest
from xml.etree import ElementTree as ET

from xmlformatter import Formatter

from pydeclares import Declared, pascalcase_var, var, vec
from pydeclares.marshals import json, xml

_xml_formatter = Formatter()


def format_xml(s: str):
    return _xml_formatter.format_string(s).decode()


class JSONSerializeTestCase(unittest.TestCase):
    def test_struct_simple_use(self):
        class Person(Declared):
            name = var(str)
            age = var(int)

        data = '{"name": "Tom", "age": 18}'
        person = Person.from_json(data)
        self.assertEqual(person.to_json(), data)

    def test_list_simple_use(self):
        class Person(Declared):
            name = var(str)
            age = var(int)

        Persons = vec(Person)
        data = '[{"name": "Tom", "age": 18}, {"name": "Jack", "age": 18}, {"name": "Jerry", "age": 18}]'
        persons = json.unmarshal(Persons, data)
        self.assertEqual(json.marshal(persons), data)

    def test_struct_inner_contain(self):
        class Home(Declared):
            location = var(str)

        class Person(Declared):
            name = var(str)
            age = var(int)
            home = var(Home)

        data = '{"name": "Tom", "age": 18, "home": {"location": "England"}}'
        person = Person.from_json(data)
        self.assertEqual(person.to_json(), data)

    def test_list_inner_contain(self):
        class Home(Declared):
            location = var(str)

        class Person(Declared):
            name = var(str)
            age = var(int)
            home = vec(Home)

        data = (
            '{"name": "Tom", "age": 18, "home": [{"location": "England"}, {"location": "China"}, '
            '{"location": "America"}]}'
        )
        person = Person.from_json(data)
        self.assertEqual(person.to_json(), data)

    def test_struct_complex_inner_contain(self):
        class Furniture(Declared):
            name = var(str)

        class Home(Declared):
            location = var(str)
            furniture = var(Furniture)

        class Person(Declared):
            name = var(str)
            age = var(int)
            home = var(Home)

        data = '{"name": "Tom", "age": 18, "home": {"location": "England", "furniture": {"name": "desk"}}}'
        person = Person.from_json(data)
        self.assertEqual(person.to_json(), data)

    def test_list_complex_inner_contain(self):
        class Furniture(Declared):
            name = var(str)

        class Home(Declared):
            location = var(str)
            furniture = var(Furniture)

        class Person(Declared):
            name = var(str)
            age = var(int)
            home = vec(Home)

        data = '{"name": "Tom", "age": 18, "home": [{"location": "England", "furniture": {"name": "desk"}}]}'
        person = Person.from_json(data)
        self.assertEqual(person.to_json(), data)


class FormDataSerializeTestCase(unittest.TestCase):
    def test_simple_use(self):
        form_data = "crcat=test&crsource=test&crkw=buy-a-lot&crint=1&crfloat=1.2"

        class Example(Declared):
            crcat = var(str)
            crsource = var(str)
            crkw = var(str)
            crint = var(int)
            crfloat = var(float)

        example = Example.from_form_data(form_data)
        self.assertEqual(example.crint, 1)
        self.assertEqual(example.crfloat, 1.2)
        self.assertEqual(example.to_form_data(), form_data)


class QueryStringSerializeTestCase(unittest.TestCase):
    def test_simple_use(self):
        query_string = "crcat=test&crsource=test&crkw=buy-a-lot&crint=1&crfloat=1.2"

        class Example(Declared):
            crcat = var(str)
            crsource = var(str)
            crkw = var(str)
            crint = var(int)
            crfloat = var(float)

        example = Example.from_query_string(query_string)
        self.assertEqual(example.crint, 1)
        self.assertEqual(example.crfloat, 1.2)
        self.assertEqual(example.to_query_string(), query_string)


class XmlSerializeTestCase(unittest.TestCase):
    def test_simple_use(self):
        xml_string = """
        <?xml version="1.0" encoding="utf-8"?>
        <data>
            <country name="Liechtenstein">
                <rank>1</rank>
                <year>2008</year>
                <gdppc>141100</gdppc>
                <neighbor name="Austria" direction="E"/>
            </country>
            <country name="Singapore">
                <rank>4</rank>
                <year>2011</year>
                <gdppc>59900</gdppc>
                <neighbor name="Malaysia" direction="N"/>
            </country>
            <country name="Panama">
                <rank>68</rank>
                <year>2011</year>
                <gdppc>13600</gdppc>
                <neighbor name="Costa Rica" direction="W"/>
            </country>
        </data>
        """.strip()

        class Neighbor(Declared):
            name = var(str, as_xml_attr=True)
            direction = var(str, as_xml_attr=True)

        class Country(Declared):
            rank = var(str)
            year = var(int)
            gdppc = var(int)
            name = var(str, as_xml_attr=True)
            neighbor = var(Neighbor)

        Data = vec(Country, field_name="country")
        data = xml.unmarshal(Data, ET.XML(xml_string))
        self.assertEqual(
            ET.tostring(xml.marshal(data, xml.Options(True))).decode(),
            '<data><country name="Liechtenstein"><rank>1</rank><year>2008</year><gdppc>141100</gdppc>'
            '<neighbor direction="E" name="Austria" /></country><country name="Singapore"><rank>4</rank>'
            '<year>2011</year><gdppc>59900</gdppc><neighbor direction="N" name="Malaysia" /></country>'
            '<country name="Panama"><rank>68</rank><year>2011</year><gdppc>13600</gdppc>'
            '<neighbor direction="W" name="Costa Rica" /></country></data>',
        )
        v = json.Vec(data.vec)
        v.extend(data)
        self.assertEqual(
            json.marshal(v),
            '[{"rank": "1", "year": 2008, "gdppc": 141100, "name": "Liechtenstein", '
            '"neighbor": {"name": "Austria", "direction": "E"}}, {"rank": "4", "year": 2011, '
            '"gdppc": 59900, "name": "Singapore", "neighbor": {"name": "Malaysia", "direction": "N"}}, '
            '{"rank": "68", "year": 2011, "gdppc": 13600, "name": "Panama", "neighbor": '
            '{"name": "Costa Rica", "direction": "W"}}]',
        )

    def test_other_simple_use(self):
        xml_string = """
        <resources>
            <style name="AppTheme" parent="Theme.AppCompat.Light.DarkActionBar">
                <item name="colorPrimary">@color/colorPrimary</item>
                <item name="colorPrimaryDark">@color/colorPrimaryDark</item>
                <item name="colorAccent">@color/colorAccent</item>
            </style>

            <style name="AppTheme.NoActionBar">
                <item name="windowActionBar">false</item>
                <item name="windowNoTitle">true</item>
            </style>

            <style name="AppTheme.AppBarOverlay" parent="ThemeOverlay.AppCompat.Dark.ActionBar" />
            <style name="AppTheme.PopupOverlay" parent="ThemeOverlay.AppCompat.Light" />

            <style name="ratingBarStyle" parent="@android:style/Widget.RatingBar">
                <item name="android:progressDrawable">@drawable/ratingbar_drawable</item>
                <item name="android:minHeight">48dip</item>
                <item name="android:maxHeight">48dip</item>
            </style>
        </resources>
        """.strip()

        class Item(Declared):
            name = var(str, as_xml_attr=True)
            text = var(str, as_xml_text=True)

        class Style(Declared):
            name = var(str, as_xml_attr=True)
            parent = var(str, as_xml_attr=True, required=False)
            items = vec(Item, field_name="item")

        Resource = vec(Style, field_name="style")
        data = xml.unmarshal(Resource, ET.XML(xml_string))
        assert len(data) == 5
        assert format_xml(ET.tostring(xml.marshal(data, xml.Options(True))).decode()) == format_xml(xml_string)
        v = json.Vec(data.vec)
        v.extend(data)
        assert (
            json.marshal(v) == '[{"name": "AppTheme", "parent": "Theme.AppCompat.Light.DarkActionBar", "item": '
            '[{"name": "colorPrimary", "text": "@color/colorPrimary"}, '
            '{"name": "colorPrimaryDark", "text": "@color/colorPrimaryDark"}, '
            '{"name": "colorAccent", "text": "@color/colorAccent"}]}, '
            '{"name": "AppTheme.NoActionBar", "parent": null, "item": ['
            '{"name": "windowActionBar", "text": "false"}, {"name": "windowNoTitle", "text": "true"}]}, '
            '{"name": "AppTheme.AppBarOverlay", "parent": "ThemeOverlay.AppCompat.Dark.ActionBar", "item": []}, '
            '{"name": "AppTheme.PopupOverlay", "parent": "ThemeOverlay.AppCompat.Light", "item": []}, '
            '{"name": "ratingBarStyle", "parent": "@android:style/Widget.RatingBar", "item": '
            '[{"name": "android:progressDrawable", "text": "@drawable/ratingbar_drawable"}, '
            '{"name": "android:minHeight", "text": "48dip"}, '
            '{"name": "android:maxHeight", "text": "48dip"}]}]'
        )
        assert (
            json.marshal(v, json.Options(True))
            == '[{"name": "AppTheme", "parent": "Theme.AppCompat.Light.DarkActionBar", "item": '
            '[{"name": "colorPrimary", "text": "@color/colorPrimary"}, '
            '{"name": "colorPrimaryDark", "text": "@color/colorPrimaryDark"}, '
            '{"name": "colorAccent", "text": "@color/colorAccent"}]}, '
            '{"name": "AppTheme.NoActionBar", "item": [{"name": "windowActionBar", "text": "false"}, '
            '{"name": "windowNoTitle", "text": "true"}]}, '
            '{"name": "AppTheme.AppBarOverlay", "parent": "ThemeOverlay.AppCompat.Dark.ActionBar", "item": []}, '
            '{"name": "AppTheme.PopupOverlay", "parent": "ThemeOverlay.AppCompat.Light", "item": []}, '
            '{"name": "ratingBarStyle", "parent": "@android:style/Widget.RatingBar", "item": '
            '[{"name": "android:progressDrawable", "text": "@drawable/ratingbar_drawable"}, '
            '{"name": "android:minHeight", "text": "48dip"}, {"name": "android:maxHeight", "text": "48dip"}]}]'
        )

    def test_declared_to_xml(self):
        xml_string = """
        <?xml version="1.0" encoding="utf-8"?>
        <person valid="true">
            <name>John</name>
            <age>18</age>
        </person>
        """.strip()

        class Person(Declared):
            valid = var(str, as_xml_attr=True)
            name = var(str)
            age = var(int)

        one_person = Person.from_xml_string(xml_string)
        self.assertEqual(one_person.name, "John")
        self.assertEqual(one_person.valid, "true")
        self.assertEqual(one_person.age, 18)
        self.assertEqual(
            one_person.to_xml_bytes().decode(),
            '<person valid="true"><name>John</name><age>18</age></person>',
        )
        self.assertEqual(one_person.to_json(), '{"valid": "true", "name": "John", "age": 18}')

    def test_c2_xml(self):
        with open("tests/c2.xml") as f:
            xml_string = f.read().strip().replace("\n", "").replace("\t", "")
        pattern = re.compile(r">\s*<")
        xml_string = pattern.sub("><", xml_string)

        class Property(Declared):
            __xml_tag_name__ = "Property"

            name = pascalcase_var(str, as_xml_attr=True)
            value = var(str, as_xml_text=True)

        class Object(Declared):
            __xml_tag_name__ = "Object"

            action = pascalcase_var(str, as_xml_attr=True)
            code = pascalcase_var(str, as_xml_attr=True)
            id_ = var(str, field_name="ID", as_xml_attr=True)
            element_type = pascalcase_var(str, as_xml_attr=True)

            properties = vec(Property, field_name="Property")

        class Mapping(Declared):
            __xml_tag_name__ = "Mapping"

            element_code = pascalcase_var(str, as_xml_attr=True)
            element_type = pascalcase_var(str, as_xml_attr=True)
            element_id = var(str, as_xml_attr=True, field_name="ElementID")
            parent_type = pascalcase_var(str, as_xml_attr=True)
            parent_code = pascalcase_var(str, as_xml_attr=True)
            parent_id = var(str, as_xml_attr=True, field_name="ParentID")
            action = pascalcase_var(str, as_xml_attr=True)

            properties = vec(Property, field_name="Property")

        class Objects(Declared):
            __xml_tag_name__ = "Objects"

            object_ = vec(Object, field_name="Object")

        class Mappings(Declared):
            __xml_tag_name__ = "Mappings"

            mapping = vec(Mapping, field_name="Mapping")

        class ADI(Declared):
            __xml_tag_name__ = "ADI"

            objects = pascalcase_var(Objects)
            mappings = pascalcase_var(Mappings)

        adi = ADI.from_xml_string(xml_string)
        self.assertMultiLineEqual(adi.to_xml_bytes(encoding="utf-8").decode("utf-8"), xml_string)

    def test_c2_xml_prettify(self):
        class VideoFormat(Declared):
            __xml_tag_name__ = "VideoFormat"

            image_width = pascalcase_var(int)
            image_height = pascalcase_var(int)
            bits_per_pixel = pascalcase_var(int)
            pixel_format = pascalcase_var(int)
            frame_rate = pascalcase_var(int)
            compression = pascalcase_var(str)
            data_rate = pascalcase_var(int)
            scan_mode = pascalcase_var(int)
            gop_size = pascalcase_var(str)
            b_frame_count = pascalcase_var(int)
            p_frame_count = pascalcase_var(int)

        class FileFormat(Declared):
            __xml_tag_name__ = "FileFormat"

            video_format = pascalcase_var(VideoFormat)

        xml_string = """<?xml version='1.0' encoding='utf8'?>
<FileFormat>
    <VideoFormat>
        <ImageWidth>1920</ImageWidth>
        <ImageHeight>1080</ImageHeight>
        <BitsPerPixel>8</BitsPerPixel>
        <PixelFormat>0</PixelFormat>
        <FrameRate>25</FrameRate>
        <Compression>11</Compression>
        <DataRate>0</DataRate>
        <ScanMode>2</ScanMode>
        <GopSize>15-25</GopSize>
        <BFrameCount>2</BFrameCount>
        <PFrameCount>4</PFrameCount>
    </VideoFormat>
</FileFormat>"""

        adi = FileFormat.from_xml_string(xml_string)
        self.assertMultiLineEqual(adi.to_xml_bytes(encoding="utf8", indent=" " * 4).decode("utf8"), xml_string)

        xml_string = """<?xml version='1.0' encoding='utf8'?>
<FileFormat>
      <VideoFormat>
            <ImageWidth>1920</ImageWidth>
            <ImageHeight>1080</ImageHeight>
            <BitsPerPixel>8</BitsPerPixel>
            <PixelFormat>0</PixelFormat>
            <FrameRate>25</FrameRate>
            <Compression>11</Compression>
            <DataRate>0</DataRate>
            <ScanMode>2</ScanMode>
            <GopSize>15-25</GopSize>
            <BFrameCount>2</BFrameCount>
            <PFrameCount>4</PFrameCount>
      </VideoFormat>
</FileFormat>"""

        adi = FileFormat.from_xml_string(xml_string)
        self.maxDiff = None
        self.assertMultiLineEqual(adi.to_xml_bytes(encoding="utf8", indent=" " * 6).decode("utf8"), xml_string)

    def test_empty_node(self):
        xml_string = """
        <?xml version="1.0" encoding="utf-8"?>
        <person valid="true">
            <name>John</name>
            <age>18</age>
        </person>
        """.strip()

        class Person(Declared):
            valid = var(str, as_xml_attr=True)
            name = var(str)
            age = var(int)

        one_person = Person.from_xml_string(xml_string)
        self.assertEqual(one_person.name, "John")
        self.assertEqual(one_person.valid, "true")
        self.assertIs(one_person.age, 18)
        self.assertEqual(
            one_person.to_xml_bytes().decode(),
            '<person valid="true"><name>John</name><age>18</age></person>',
        )
        self.assertEqual(one_person.to_json(), '{"valid": "true", "name": "John", "age": 18}')
        self.assertEqual(
            one_person.to_xml_bytes(skip_none_field=True).decode(),
            '<person valid="true"><name>John</name><age>18</age></person>',
        )
        self.assertEqual(
            one_person.to_json(skip_none_field=True),
            '{"valid": "true", "name": "John", "age": 18}',
        )
