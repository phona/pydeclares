# PyDeclares

This library provides a simple API for encoding and decoding declared classes to and from JSON, XML, FORM-DATA or QueryString.

It's very easy to get started.

## Quickstart

`pip install pydeclares`

```python
from pydeclares import var, Declared

class Person(Declared):
	name = var(str)
	age = var(int)

# decode json string
data = '{"name": "Tom", "age": 18}'
person = Person.from_json(data)

assert person.name == "Tom"
assert person.age == 18

# you can encode to xml after decode json string
result = person.to_xml()

assert result == '<person><name>Tom</name><age>18</age></person>'

# or form-data
result = person.to_form_data()

assert result == "name=Tom&age=18"

# or query string
person = Person(name="tom@a", age=18)
result = person.to_query_string()

assert result == "name=tom%40a&age=18"
```