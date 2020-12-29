from functools import lru_cache
import json
import re
import urllib.parse as urlparse
from collections import UserList
from decimal import Decimal
from json.decoder import JSONDecoder
from typing import (
    Any,
    AnyStr,
    Callable,
    ClassVar,
    Collection,
    Dict, Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from xml.etree import ElementTree as ET

from pydeclares import variables
from pydeclares import variables as vars
from pydeclares.codecs import CodecNotFoundError, encode
from pydeclares.defines import MISSING, Json, JsonData
from pydeclares.utils import isinstance_safe, issubclass_safe, xml_prettify

Var = variables.Var
CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>")

_T = TypeVar("_T")
_DT = TypeVar("_DT", bound="Declared")


def custom_escape_cdata(text: str) -> str:
    if not isinstance_safe(text, str):
        text = str(text)

    if CDATA_PATTERN.match(text):
        return text
    return ET_escape_cdata(text)


ET_escape_cdata = ET._escape_cdata
ET._escape_cdata = custom_escape_cdata


class BaseDeclared(type):
    def __new__(
        cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]
    ) -> "BaseDeclared":
        if name == "Declared":
            return super(BaseDeclared, cls).__new__(cls, name, bases, namespace)

        fields: List[str] = []
        meta_vars: Dict[str, "Var[Any, Any]"] = {}
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

        for key in list(namespace.keys()):
            if isinstance(namespace[key], Var):
                if key not in fields:
                    fields.append(key)
                var = namespace.pop(key)
                var.name = key
                meta_vars[key] = var

        meta = {"vars": meta_vars}
        new_cls: Any = super(BaseDeclared, cls).__new__(cls, name, bases, namespace)
        setattr(new_cls, "fields", tuple(fields))
        setattr(new_cls, "meta", meta)
        return new_cls


class Declared(metaclass=BaseDeclared):
    """ declared a serialize object make data class more clearly and flexible, provide
    default serialize function and well behavior hash, str and eq.
    fields can use None object represent null or empty situation, otherwise those fields
    must be provided unless set it required as False.
    """

    __xml_tag_name__ = ""
    fields: ClassVar[Tuple[str]]
    meta: ClassVar[Dict[str, "vars.Var[Any, Any]"]]

    def __init__(self, *args: Any, **kwargs: Any):
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
                        f"please set `init` argument to False for this variable."
                    )

            if not field.type_checking(field_value):
                field_value = field.cast_it(field_value)
            setattr(self, field.name, field_value)

        self.__post_init__(**omits)
        self._is_empty = False

    def __post_init__(self, **omits: Any):
        """"""

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

    def to_json(
        self,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: Union[None, int, str] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable[[Any], Json]] = None,
        sort_keys: bool = False,
        skip_none_field: bool = False,
        **kw: Any,
    ):
        return json.dumps(
            self.to_dict(encode_json=False, skip_none_field=skip_none_field),
            cls=_ExtendedEncoder,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )

    @classmethod
    def from_json(
        cls: Type["Declared"],
        s: JsonData,
        *,
        encoding: Optional[Type[JSONDecoder]] = None,
        parse_float: Optional[Callable[[str], Any]] = None,
        parse_int: Optional[Callable[[str], Any]] = None,
        parse_constant: Optional[Callable[[str], Any]] = None,
        **kw: Any,
    ):
        kvs = json.loads(
            s,
            encoding=encoding,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            **kw,
        )
        return cls.from_dict(kvs)

    @classmethod
    def from_dict(cls: Type[_DT], kvs: Dict[str, Any]) -> _DT:
        init_kwargs = {}
        for field in fields(cls):
            try:
                field_value = kvs[field.field_name]
                if issubclass(field.type_, Declared):
                    field_value = field.type_.from_dict(field_value)
            except KeyError:
                default = field.make_default()
                if default is None:
                    continue
                field_value = default

            init_kwargs[field.name] = field_value

        return cls(**init_kwargs)

    def to_dict(
        self, encode_json: bool = False, skip_none_field: bool = False
    ) -> Dict[str, Any]:
        result = []
        field: Var[Any, Any]
        for field in fields(self):
            if field.ignore_serialize:
                continue

            field_value = getattr(self, field.name, MISSING)
            if field_value is MISSING:
                field_value = field.make_default()
                if field_value is None:
                    if not field.required:
                        continue
                    else:
                        raise AttributeError(f"field {field.name} is required.")

            if skip_none_field and field_value is None:
                continue

            if isinstance_safe(field_value, Declared):
                field_value = self.to_dict(encode_json, skip_none_field,)

            result.append((field.field_name, field_value))

        return _encode_overrides(dict(result), encode_json)

    @classmethod
    def from_form_data(cls: Type["Declared"], form_data: str):
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(urlparse.parse_qsl(form_data)))

    def to_form_data(self, skip_none_field: bool = False):
        if self.has_nest_declared_class():
            raise ValueError("can't serialize with nested declared class.")

        data = self.to_dict(skip_none_field=skip_none_field)
        for k, v in data.items():
            try:
                data[k] = encode(v)
            except CodecNotFoundError:
                pass

        return "&".join([f"{k}={v}" for k, v in data.items()])

    @classmethod
    def from_query_string(cls: Type["Declared"], query_string: str):
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(urlparse.parse_qsl(query_string)))

    def to_query_string(
        self,
        skip_none_field: bool = False,
        doseq: bool = False,
        safe: str = "",
        encoding: str = "",
        errors: str = "",
        quote_via: Callable[[str, AnyStr, str, str], str] = urlparse.quote_plus,
    ):
        if self.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        data = self.to_dict(skip_none_field=skip_none_field)
        for k, v in data.items():
            try:
                data[k] = encode(v)
            except CodecNotFoundError:
                pass

        return urlparse.urlencode(
            data,
            doseq=doseq,
            safe=safe,
            encoding=encoding,
            errors=errors,
            quote_via=quote_via,
        )

    @classmethod
    def from_xml(cls: Type["Declared"], element: ET.Element) -> "Declared":
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
        init_kwargs: Dict[str, Any] = {}
        for field in fields(cls):
            if field.as_xml_attr:
                field_value = element.get(field.field_name, MISSING)
            elif field.as_xml_text:
                field_value = element.text
            elif issubclass_safe(field.type_, List):
                subs = element.findall(field.field_name)
                field_value = field.type_.from_xml_list(subs, element.tag)
            elif issubclass_safe(field.type_, Declared):
                sub = element.find(field.field_name)
                if sub is None:
                    sub = MISSING
                field_value = field.type_.from_xml(sub)
            else:
                field_value = getattr(element.find(field.field_name), "text", MISSING)

            init_kwargs[field.name] = field.cast_it(field_value)

        return cls(**init_kwargs)

    @classmethod
    def from_xml_string(cls: Type["Declared"], xml_string: str) -> "Declared":
        return cls.from_xml(ET.XML(xml_string))

    def to_xml(
        self, skip_none_field: bool = False, indent: Optional[str] = None
    ) -> ET.Element:
        """
        <?xml version="1.0"?>
        <tag id="`id`" style="`style`">
            `text`
        </tag>
        """
        tag = (
            self.__xml_tag_name__
            if self.__xml_tag_name__
            else self.__class__.__name__.lower()
        )
        root = ET.Element(tag)
        for field in fields(self):
            if field.as_xml_attr:
                # handle attributes
                new_attr = getattr(self, field.name, "")
                if new_attr and new_attr is not MISSING:
                    try:
                        attr = str(encode(new_attr))
                    except CodecNotFoundError:
                        attr = str(new_attr)
                    root.set(field.field_name, attr)
            elif field.as_xml_text:
                # handle has multiple attributes and text element, like <country size="large">Panama</country>
                text = getattr(self, field.name, "")
                if text:
                    try:
                        text = str(encode(text))
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
                field_value = getattr(self, field.name, MISSING)
                elem = ET.Element(field.field_name)
                if field_value is not MISSING and field_value is not None:
                    try:
                        text = str(encode(field_value))
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

    def to_xml_bytes(
        self, skip_none_field: bool = False, indent: Optional[str] = None, **kwargs: Any
    ) -> bytes:
        return ET.tostring(self.to_xml(skip_none_field, indent), **kwargs)

    @classmethod
    def empty(cls):
        inst = cls.__new__(cls)
        for f in fields(cls):
            setattr(inst, f.name, MISSING)
        inst._is_empty = True
        return inst

    def __bool__(self):
        return not self._is_empty

    def __str__(self):
        args = [
            f"{field_name}={str(getattr(self, field_name, 'missing'))}"
            for field_name in self.fields
        ]
        return f"{self.__class__.__name__}({','.join(args)})"

    def __eq__(self, other: "Declared"):
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


class GenericList(List[_T], UserList):  # type: ignore
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

    __type__: ClassVar[Type[_T]]

    def __init__(self, initlist: Iterable[_T] = [], tag: Optional[str] = None):
        if self.__type__ is None:
            raise TypeError(
                f"Type {self.__class__.__name__} cannot be intialize directly; please use new_list_type instead"
            )

        if isinstance_safe(self.__type__, Declared):
            super().__init__((self.__type__.from_dict(i) for i in initlist))  # type: ignore
        else:
            super().__init__(initlist)
        # type checked
        for item in self.data:
            if not isinstance_safe(item, self.__type__):
                raise TypeError(
                    f"Type of instance {str(item)} is {type(item)}, but not {self.__type__}."
                )
        self.tag = tag

    @classmethod
    def from_json(
        cls: Type["GenericList[_T]"],
        s: JsonData,
        *,
        parse_float: Optional[Callable[[str], Any]] = None,
        parse_int: Optional[Callable[[str], Any]] = None,
        parse_constant: Optional[Callable[[str], Any]] = None,
        **kw: Any,
    ) -> "GenericList[_T]":
        kvs = json.loads(
            s,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            **kw,
        )
        assert isinstance(kvs, List)
        return cls(kvs)  # type: ignore

    def to_json(
        self,
        skipkeys: bool = False,
        ensure_ascii: bool = True,
        check_circular: bool = True,
        allow_nan: bool = True,
        indent: Optional[Union[int, str]] = None,
        separators: Optional[Tuple[str, str]] = None,
        default: Optional[Callable[[Any], Json]] = None,
        sort_keys: bool = False,
        skip_none_field: bool = False,
        **kw: Any,
    ) -> str:
        li: List[Json]
        if issubclass_safe(self.__type__, Declared):
            li = [
                inst.to_dict(encode_json=False, skip_none_field=skip_none_field)  # type: ignore
                for inst in self.data
            ]
        else:
            li = [_encode_json_type(inst) for inst in self.data]

        return json.dumps(
            li,
            cls=_ExtendedEncoder,
            skipkeys=skipkeys,
            ensure_ascii=ensure_ascii,
            check_circular=check_circular,
            allow_nan=allow_nan,
            indent=indent,
            separators=separators,
            default=default,
            sort_keys=sort_keys,
            **kw,
        )

    @classmethod
    def from_xml(
        cls: "Type[GenericList[_T]]", element: ET.Element
    ) -> "GenericList[_T]":
        if issubclass(cls.__type__, Declared):
            t: Type[Declared] = cls.__type__
            return cls((t.from_xml(sub) for sub in element), tag=element.tag)
        return None

    @classmethod
    def from_xml_list(
        cls: Type["GenericList[_T]"], elements: List[ET.Element], tag: str
    ) -> "GenericList[_T]":
        if issubclass(cls.__type__, Declared):
            t: Type[Declared] = cls.__type__
            return cls((t.from_xml(sub) for sub in elements), tag=tag)
        return cls((sub for sub in elements), tag=tag)

    @classmethod
    def from_xml_string(
        cls: "Type[GenericList[_T]]", xml_string: str
    ) -> "GenericList[_T]":
        return cls.from_xml(ET.XML(xml_string))

    def to_xml(
        self,
        tag: Optional[str] = None,
        skip_none_field: bool = False,
        indent: Optional[str] = None,
    ) -> ET.Element:
        if tag is None:
            tag = self.tag
        root = ET.Element(tag)
        for item in self:
            root.append(item.to_xml(skip_none_field=skip_none_field))

        if indent is not None:
            xml_prettify(root, indent, "\n")

        return root

    def to_xml_bytes(
        self,
        tag: Optional[str] = None,
        skip_none_field: bool = False,
        indent: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        return ET.tostring(self.to_xml(tag, skip_none_field, indent), **kwargs)

    def __str__(self):
        return f"{self.__class__.__name__}({', '.join(str(i) for i in self)})"


class _ExtendedEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Json:
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


@lru_cache()
def new_list_type(type_: Type[_T]) -> "Type[GenericList[_T]]":
    return type(
        f"GenericList<{type_.__name__}>", (GenericList[_T],), {"__type__": type_}
    )


def _is_declared_instance(obj: object) -> bool:
    return isinstance_safe(obj, Declared)


def fields(class_or_instance: Union[Type, object]) -> Tuple[Var[Any, Any]]:
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
        raise TypeError("must be called with a declared type or instance")

    # Exclude pseudo-fields.  Note that fields is sorted by insertion
    # order, so the order of the tuple is as the fields were defined.
    out = []
    for f in fields:
        var = meta_vars.get(f, None)
        if var:
            out.append(var)
    return tuple(out)


def _encode_json_type(
    value: Any, default: Callable[[Any], Json] = _ExtendedEncoder().default
) -> Json:
    if isinstance(value, Json.__args__):  # type: ignore
        return value
    return default(value)


def _encode_overrides(kvs: Dict[Any, Any], encode_json: bool = False) -> Dict[Any, Any]:
    override_kvs = {}
    for k, v in kvs.items():
        if encode_json:
            v = _encode_json_type(v)
        override_kvs[k] = v
    return override_kvs
