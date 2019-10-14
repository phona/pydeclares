import copy
import json
import re
import urllib.parse as urlparse
from collections import UserList
from decimal import Decimal
from typing import (Any, Callable, Collection, Dict, List, Mapping, Optional,
                    Tuple, Type, Union)
from xml.etree import ElementTree as ET

from pydeclares.codecs import CodecNotFoundError, decode, encode
from pydeclares.defines import (_REGISTER_DECLARED_CLASS, MISSING, Json,
                                JsonData)
from pydeclares.utils import isinstance_safe, issubclass_safe, xml_prettify
from pydeclares.variables import Var

CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>")


def custom_escape_cdata(text):
    if not isinstance_safe(text, str):
        text = str(text)

    if CDATA_PATTERN.match(text):
        return text
    return ET_escape_cdata(text)


ET_escape_cdata = ET._escape_cdata
ET._escape_cdata = custom_escape_cdata


class BaseDeclared(type):
    def __new__(cls, name, bases, attrs):
        if name == "Declared":
            return super(BaseDeclared, cls).__new__(cls, name, bases, attrs)

        fields = []
        meta_vars = {}
        for base in bases:
            meta = getattr(base, "meta", None)
            if meta:
                base_meta_vars = meta.get("vars", {})
                meta_vars.update(base_meta_vars)
                fields.extend(base_meta_vars.keys())

            for k, v in base.__dict__.items():
                if isinstance_safe(v, Var):
                    fields.append(k)
                    var = v
                    var.name = k
                    meta_vars[k] = var

        for key in list(attrs.keys()):
            if isinstance(attrs[key], Var):
                if key not in fields:
                    fields.append(key)
                var = attrs.pop(key)
                var.name = key
                meta_vars[key] = var

        meta = {"vars": meta_vars}
        new_cls = super(BaseDeclared, cls).__new__(cls, name, bases, attrs)
        _REGISTER_DECLARED_CLASS[name] = new_cls
        new_cls.add_attribute("fields", tuple(fields))
        new_cls.add_attribute("meta", meta)
        new_cls.add_attribute("__annotations__", meta_vars)
        return new_cls

    def add_attribute(cls, name, attr):
        setattr(cls, name, attr)


class Declared(metaclass=BaseDeclared):
    """ declared a serialize object make data class more clearly and flexible, provide
    default serialize function and well behavior hash, str and eq.
    fields can use None object represent null or empty situation, otherwise those fields
    must be provided unless set it required as False.
    """

    __xml_tag_name__ = ""

    def __init__(self, *args, **kwargs):
        kwargs.update(dict(zip(self.fields, args)))
        fs = fields(self)
        omits = {}
        for field in fs:
            field_value = kwargs.get(field.name, MISSING)

            # set `init` to False but `required` is True, that mean is this variable must be init in later
            # otherwise seiralize will be failed.
            # `init` just tell Declared class use custom initializer instead of default initializer.
            if not field.init:
                if field_value is not MISSING:
                    omits[field.name] = field_value
                continue

            if field_value is MISSING:
                field_value = field.make_default()
                if field_value is MISSING and field.required:
                    raise AttributeError(
                        f"field {field.name!r} is required. if you doesn't want to init this variable in initializer, "
                        f"please set `init` argument to False for this variable.")
            setattr(self, field.name, field_value)

        self.__post_init__(**omits)

    def __post_init__(self, **omits):
        """"""

    def __setattr__(self, name, value):
        if name in self.fields:
            self.meta["vars"][name].check(value)
        super().__setattr__(name, value)

    def __getattr__(self, name):
        try:
            result = self.__getattribute__(name)
            if result is MISSING:
                return None
            return result
        except AttributeError as why:
            try:
                meta_var = self.meta["vars"][name]
            except KeyError:
                raise why
            else:
                value = meta_var.make_default()
                if value is MISSING:
                    return None
                else:
                    super().__setattr__(name, value)
                    return value

    @classmethod
    def has_nest_declared_class(cls):
        _has_nest_declared_class = getattr(cls, "_has_nest_declared_class", None)
        if _has_nest_declared_class is None:
            result = False
            for field in fields(cls):
                if _is_declared_instance(field.type_):
                    result = True
                    break
            setattr(cls, "_has_nest_declared_class", result)
        else:
            return _has_nest_declared_class

    def to_json(self,
                skipkeys: bool = False,
                ensure_ascii: bool = True,
                check_circular: bool = True,
                allow_nan: bool = True,
                indent: Optional[Union[int, str]] = None,
                separators: Tuple[str, str] = None,
                default: Callable = None,
                sort_keys: bool = False,
                skip_none_field=False,
                **kw):
        return json.dumps(self.to_dict(encode_json=False, skip_none_field=skip_none_field),
                          cls=_ExtendedEncoder,
                          skipkeys=skipkeys,
                          ensure_ascii=ensure_ascii,
                          check_circular=check_circular,
                          allow_nan=allow_nan,
                          indent=indent,
                          separators=separators,
                          default=default,
                          sort_keys=sort_keys,
                          **kw)

    @classmethod
    def from_json(cls: Type['Declared'],
                  s: JsonData,
                  *,
                  encoding=None,
                  parse_float=None,
                  parse_int=None,
                  parse_constant=None,
                  **kw):
        kvs = json.loads(s,
                         encoding=encoding,
                         parse_float=parse_float,
                         parse_int=parse_int,
                         parse_constant=parse_constant,
                         **kw)
        return cls.from_dict(kvs)

    @classmethod
    def from_dict(cls: Type['Declared'], kvs: dict):
        return _decode_dict_to_declared_class(cls, kvs)

    def to_dict(self, encode_json=False, skip_none_field=False):
        return _asdict(self, encode_json=encode_json, skip_none_field=skip_none_field)

    @classmethod
    def from_form_data(cls: Type['Declared'], form_data):
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(d.split("=") for d in form_data.split("&")))

    def to_form_data(self, skip_none_field=False):
        if self.has_nest_declared_class():
            raise ValueError("can't serialize with nested declared class.")

        return "&".join([f"{k}={v}" for k, v in self.to_dict(skip_none_field=skip_none_field).items()])

    @classmethod
    def from_query_string(cls: Type['Declared'], query_string: str):
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(d.split("=") for d in urlparse.unquote(query_string).split("&")))

    def to_query_string(self,
                        skip_none_field=False,
                        doseq=False,
                        safe='',
                        encoding=None,
                        errors=None,
                        quote_via=urlparse.quote_plus):
        if self.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return urlparse.urlencode(self.to_dict(skip_none_field=skip_none_field),
                                  doseq=doseq,
                                  safe=safe,
                                  encoding=encoding,
                                  errors=errors,
                                  quote_via=quote_via)

    @classmethod
    def from_xml(cls: Type['Declared'], element: ET.Element) -> ET.Element:
        """
        >>> class Struct(Declared):
        >>>     tag = var(str)
        >>>     text = var(str)
        >>>     children = var(str)

        >>>     # attrs
        >>>     id = var(str)
        >>>     style = var(str)
        >>>     ......
        """
        return _decode_xml_to_declared_class(cls, element)

    @classmethod
    def from_xml_string(cls: Type['Declared'], xml_string: str) -> ET.Element:
        return cls.from_xml(ET.XML(xml_string))

    def to_xml(self, skip_none_field: bool = False, indent: str = None) -> ET.Element:
        """
        <?xml version="1.0"?>
        <tag id="`id`" style="`style`">
            `text`
        </tag>
        """
        tag = self.__xml_tag_name__ if self.__xml_tag_name__ else self.__class__.__name__.lower()
        root = ET.Element(tag)
        for field in fields(self):
            if field.as_xml_attr:
                # handle attributes
                new_attr = getattr(self, field.name, "")
                if new_attr:
                    try:
                        attr = str(decode(field.type_, new_attr))
                    except CodecNotFoundError:
                        attr = str(new_attr)
                    root.set(field.field_name, attr)
            elif field.as_xml_text:
                # handle has multiple attributes and text element, like <country size="large">Panama</country>
                text = getattr(self, field.name, "")
                if text:
                    try:
                        text = str(decode(field.type_, text))
                    except CodecNotFoundError:
                        """"""
                elif not skip_none_field:
                    text = ""
                root.text = text
            elif issubclass_safe(field.type_, GenericList):
                # handle a series of struct or native type data
                field_value = getattr(self, field.name, MISSING)
                if field_value is not MISSING:
                    root.extend(field_value.to_xml(skip_none_field))
            elif issubclass_safe(field.type_, Declared):
                # handle complex struct data
                field_value = getattr(self, field.name, MISSING)
                if field_value is not MISSING:
                    root.append(field_value.to_xml(skip_none_field))
            else:
                # handle simple node just like <name>John</name>
                field_value = getattr(self, field.name, None)
                elem = ET.Element(field.field_name)
                if field_value is not None:
                    try:
                        text = str(decode(field.type_, field_value))
                    except CodecNotFoundError:
                        text = str(field_value)
                    elem.text = text
                    root.append(elem)
                elif not skip_none_field:
                    elem.text = ""
                    root.append(elem)

        if indent is not None:
            xml_prettify(root, indent, "\n")

        return root

    def to_xml_bytes(self, skip_none_field: bool = False, indent: str = None, **kwargs) -> bytes:
        return ET.tostring(self.to_xml(skip_none_field, indent), **kwargs)

    def __str__(self):
        args = [f"{var.name}={str(getattr(self, var.name, 'missing'))}" for _, var in self.meta["vars"].items()]
        return f"{self.__class__.__name__}({','.join(args)})"

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False

        for field_name in self.fields:
            field_value_self = getattr(self, field_name, MISSING)
            field_value_other = getattr(other, field_name, MISSING)
            if field_value_self != field_value_other:
                return False
        return True

    def __hash__(self):
        return hash(tuple(str(getattr(self, f.name)) for f in fields(self)))


class GenericList(UserList):
    """ represant a series of vars

    >>> class NewType(Declared):
    >>>     items = var(new_list_type(str))

    >>> result = NewType.from_json("{\"items\": [\"1\", \"2\"]}")
    >>> result.to_json() #  {\"items\": [\"1\", \"2\"]}

    or used directly

    >>> strings = new_list_type(str)
    >>> result = strings.from_json("[\"1\", \"2\"]")
    >>> result.to_json() #  "[\"1\", \"2\"]"
    """

    __type__ = None

    def __init__(self, initlist: List = [], tag: str = None):
        if self.__type__ is None:
            raise TypeError(
                f"Type {self.__class__.__name__} cannot be intialize directly; please use new_list_type instead")

        super().__init__((self.__type__.from_dict(i) for i in initlist))
        # type checked
        for item in self.data:
            if not isinstance_safe(item, self.__type__):
                raise TypeError(f"Type of instance {str(item)} is {type(item)}, but not {self.__type__}.")
        self.tag = tag

    @classmethod
    def from_json(cls: Type['GenericList'],
                  s: JsonData,
                  *,
                  encoding=None,
                  parse_float=None,
                  parse_int=None,
                  parse_constant=None,
                  **kw) -> 'GenericList':
        kvs = json.loads(s,
                         encoding=encoding,
                         parse_float=parse_float,
                         parse_int=parse_int,
                         parse_constant=parse_constant,
                         **kw)
        return cls((cls.__type__.from_dict(i) for i in kvs))

    def to_json(self,
                skipkeys: bool = False,
                ensure_ascii: bool = True,
                check_circular: bool = True,
                allow_nan: bool = True,
                indent: Optional[Union[int, str]] = None,
                separators: Tuple[str, str] = None,
                default: Callable = None,
                sort_keys: bool = False,
                skip_none_field=False,
                **kw) -> JsonData:
        return json.dumps([inst.to_dict(encode_json=False, skip_none_field=skip_none_field) for inst in self.data],
                          cls=_ExtendedEncoder,
                          skipkeys=skipkeys,
                          ensure_ascii=ensure_ascii,
                          check_circular=check_circular,
                          allow_nan=allow_nan,
                          indent=indent,
                          separators=separators,
                          default=default,
                          sort_keys=sort_keys,
                          **kw)

    @classmethod
    def from_xml(cls: Type['GenericList'], element: ET.Element) -> 'GenericList':
        return cls((cls.__type__.from_xml(sub) for sub in element), tag=element.tag)

    @classmethod
    def from_xml_list(cls: Type['GenericList'], elements: List[ET.Element], tag) -> 'GenericList':
        return cls((cls.__type__.from_xml(sub) for sub in elements), tag=tag)

    @classmethod
    def from_xml_string(cls: Type['GenericList'], xml_string) -> 'GenericList':
        return cls.from_xml(ET.XML(xml_string))

    def to_xml(self, tag: str = None, skip_none_field: bool = False, indent: str = None) -> ET.Element:
        if tag is None:
            tag = self.tag
        root = ET.Element(tag)
        for item in self:
            root.append(item.to_xml(skip_none_field=skip_none_field))

        if indent is not None:
            xml_prettify(root, indent, "\n")

        return root

    def to_xml_bytes(self, tag: str = None, skip_none_field: bool = False, indent: str = None, **kwargs) -> bytes:
        return ET.tostring(self.to_xml(tag, skip_none_field, indent), **kwargs)

    def __str__(self):
        return f"{self.__class__.__name__}({', '.join(str(i) for i in self)})"


__created_list_types: Dict[Type, GenericList] = {}


class _ExtendedEncoder(json.JSONEncoder):
    def default(self, o):
        result: Json
        if isinstance_safe(o, Collection):
            if isinstance_safe(o, Mapping):
                result = dict(o)
            else:
                result = list(o)
        elif isinstance_safe(o, Decimal):
            result = str(o)
        else:
            try:
                result = encode(o)
            except CodecNotFoundError:
                result = json.JSONEncoder.default(self, o)
        return result


def new_list_type(type_: Type) -> GenericList:
    if type_ in __created_list_types:
        return __created_list_types[type_]
    cls = type(f"GenericList<{type_.__name__}>", (GenericList, ), {"__type__": type_})
    __created_list_types[type_] = cls
    return cls


def _decode_xml_to_declared_class(cls: Type[Declared], element: ET.Element) -> Declared:
    init_kwargs: Dict[str, Any] = {}
    for field in fields(cls):
        if field.as_xml_attr:
            field_value = element.get(field.field_name, MISSING)
        elif field.as_xml_text:
            field_value = element.text
        elif issubclass_safe(field.type_, GenericList):
            subs = element.findall(field.field_name)
            field_value = field.type_.from_xml_list(subs, element.tag)
        elif issubclass_safe(field.type_, Declared):
            sub = element.find(field.field_name)
            if sub is None:
                sub = MISSING
            field_value = field.type_.from_xml(sub)
        else:
            field_value = element.find(field.field_name).text
        init_kwargs[field.name] = _cast_field_value(field, field_value)
    return cls(**init_kwargs)


def _decode_dict_to_declared_class(cls: Type[Declared], kvs: Union['List', 'Dict']):
    if isinstance_safe(kvs, cls):
        return kvs

    if not kvs:
        if issubclass_safe(cls, Declared):
            return cls.__new__(cls)
        return cls()

    init_kwargs: Dict[str, Any] = {}
    for field in fields(cls):
        field_value = kvs.get(field.field_name, MISSING)
        if field_value is MISSING:
            field_value = field.make_default()

        init_kwargs[field.name] = _cast_field_value(field, field_value)

    return cls(**init_kwargs)


def _cast_field_value(field: Var, field_value: Any):
    if field_value is MISSING:
        return field_value

    if issubclass_safe(field.type_, Declared):
        value = _decode_dict_to_declared_class(field.type_, field_value)
    elif issubclass_safe(field.type_, Decimal):
        value = field_value if isinstance(field_value, Decimal) else Decimal(field_value)
    else:
        try:
            value = decode(field.type_, field_value)
        except CodecNotFoundError:
            if type(field_value) != field.type_ and field.auto_cast and field and field_value:
                try:
                    value = field.type_(field_value)
                except ValueError as why:
                    raise ValueError(
                        f"{why}: field {field.name} does't support cast type {type(field_value)}({field_value!r}) to {field.type_},"
                        f"if you want to avoid this cast in here just turn off `auto_cast` when you define this variable."
                    )
            else:
                value = field_value
    return value


def _is_declared_instance(obj: object) -> bool:
    return isinstance_safe(obj, Declared)


def fields(class_or_instance: Union[Type, object]) -> Tuple[Var]:
    """Return a tuple describing the fields of this declared class.
    Accepts a declared class or an instance of one. Tuple elements are of
    type Field.
    """
    # Might it be worth caching this, per class?
    try:
        fields = getattr(class_or_instance, "fields")
        meta = getattr(class_or_instance, "meta")
        meta_vars = meta["vars"]
    except AttributeError or KeyError:
        raise TypeError('must be called with a declared type or instance')

    # Exclude pseudo-fields.  Note that fields is sorted by insertion
    # order, so the order of the tuple is as the fields were defined.
    out = []
    for f in fields:
        var: Var = meta_vars.get(f, None)
        if var:
            out.append(var)
    return tuple(out)


def _encode_json_type(value, default=_ExtendedEncoder().default):
    if isinstance(value, Json.__args__):
        return value
    return default(value)


def _encode_overrides(kvs, overrides, encode_json=False):
    override_kvs = {}
    for k, v in kvs.items():
        # if k in overrides:
        #     letter_case = overrides[k].letter_case
        #     original_key = k
        #     k = letter_case(k) if letter_case is not None else k

        #     encoder = overrides[original_key].encoder
        #     v = encoder(v) if encoder is not None else v

        if encode_json:
            v = _encode_json_type(v)
        override_kvs[k] = v
    return override_kvs


def _asdict(obj, encode_json=False, skip_none_field=False):
    if _is_declared_instance(obj):
        result = []
        field: Var
        for field in fields(obj):
            if field.ignore_serialize:
                continue

            field_value = obj.__dict__.get(field.name, MISSING)
            if field_value is MISSING:
                field_value = field.make_default()
                if field_value is MISSING:
                    if not field.required:
                        field_value = None
                    else:
                        raise AttributeError(f"field {field.name} is required.")

            if skip_none_field and field_value is None:
                continue

            value = _asdict(field_value, encode_json=encode_json, skip_none_field=skip_none_field)
            result.append((field.field_name, value))
        return _encode_overrides(dict(result), None, encode_json=encode_json)
    elif isinstance(obj, Mapping):
        return dict((_asdict(k, encode_json=encode_json), _asdict(v, encode_json=encode_json)) for k, v in obj.items())
    elif isinstance(obj, Collection) and not isinstance(obj, str):
        return list(_asdict(v, encode_json=encode_json) for v in obj)
    else:
        return copy.deepcopy(obj)
