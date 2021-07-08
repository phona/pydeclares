import urllib.parse as urlparse
from json.decoder import JSONDecoder
from json.encoder import JSONEncoder
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from xml.etree import ElementTree as ET

from pydeclares import variables, variables as vars
from pydeclares.defines import MISSING, JsonData
from pydeclares.exceptions import FieldRequiredError
from pydeclares.marshals import json, xml
from pydeclares.utils import isinstance_safe, xml_prettify

Var = variables.Var

_T = TypeVar("_T")
_DT = TypeVar("_DT", bound="Declared")


class BaseDeclared(type):
    def __new__(cls, name, bases, namespace):
        # type: (str, Tuple[type, ...], Dict[str, Any]) -> BaseDeclared
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
    """declared a serialize object make data class more clearly and flexible, provide
    default serialize function and well behavior hash, str and eq.
    fields can use None object represent null or empty situation, otherwise those fields
    must be provided unless set it required as False.
    """

    __xml_tag_name__ = ""
    fields: ClassVar[Tuple[str]]
    meta: ClassVar[Dict[str, "vars.Var[Any, Any]"]]

    def __init__(self, *args, **kwargs):
        # type: (Any, Any) -> None
        kwargs.update(dict(zip(self.fields, args)))
        omits = {}
        omit_fields = []  # type: List[variables.Var]
        for field in fields(self):
            field_value = kwargs.get(field.name, MISSING)

            if field_value is MISSING:
                field_value = field.make_default()

            # set `init` to False but `required` is True, that mean is this variable must be init in later
            # otherwise seiralize will be failed.
            # `init` just tell Declared class use custom initializer instead of default initializer.
            if not field.init:
                if field_value is not MISSING:
                    omits[field.name] = field_value
                    omit_fields.append(field)
                continue

            self._setattr(field, field_value)

        self.__post_init__(**omits)
        self._is_empty = False

        for field in omit_fields:
            value = getattr(self, field.name, MISSING)
            if value is MISSING:
                raise FieldRequiredError(
                    f"field `{field.name}` is marked that initialize by user on __post_init__ method"
                    " but it has not been seted on there"
                )

            self._setattr(field, value)

    def _setattr(self, field, field_value):
        # type: (variables.Var, Optional[Any]) -> None
        if field_value is None and field.required:
            raise FieldRequiredError(
                f"field `{field.name}` is required. if you couldn't know whether it is existed or not, "
                f"set a default value or default factory function to this field for erase this error."
            )

        can_skip_field_checking = field_value is None and not field.required
        if not can_skip_field_checking and not field.type_checking(field_value):
            field_value = field.cast_it(field_value)
        setattr(self, field.name, field_value)

    def __post_init__(self, **omits: Any):
        """"""

    @classmethod
    def has_nest_declared_class(cls):
        _has_nest_declared_class = getattr(cls, "_has_nest_declared_class", None)
        if _has_nest_declared_class is None:
            result = False
            for field in fields(cls):
                if isinstance_safe(field.type_, Declared):
                    result = True
                    break
            setattr(cls, "_has_nest_declared_class", result)
        else:
            return _has_nest_declared_class

    @classmethod
    def from_dict(cls, kvs, enable_serializer=False):
        # type: (Type[_DT], Dict[str, Any], bool) -> _DT
        init_kwargs = {}
        for field in fields(cls):
            try:
                field_value = kvs[field.field_name]
                if issubclass(field.type_, Declared):
                    field_value = field.type_.from_dict(field_value)
                elif (
                    issubclass(field.type_, List)
                    and isinstance(field, variables.vec)
                    and issubclass(field.item_type, Declared)
                ):
                    assert isinstance(
                        field_value, Iterable
                    ), f"field `{field.name}` cannot receive not iterable type"
                    field_value = [field.item_type.from_dict(v) for v in field_value]
                elif (
                    issubclass(field.type_, Dict)
                    and isinstance(field, variables.kv)
                    and issubclass(field.v_type, Declared)
                ):
                    assert isinstance(
                        field_value, Iterable
                    ), f"field `{field.name}` cannot receive not iterable type"
                    field_value = {k: field.v_type.from_dict(v) for k, v in field_value.items()}
            except KeyError:
                default = field.make_default()
                if default is None:
                    continue
                field_value = default

            if field.serializer and enable_serializer:
                field_value = field.serializer.to_internal_value(field_value)

            init_kwargs[field.name] = field_value

        return cls(**init_kwargs)

    def to_dict(self, skip_none_field=False, enable_serializer=False):
        # type: (bool, bool) -> Dict[str, Any]
        result = []
        field: Var[Any, Any]
        for field in fields(self):
            if field.ignore_serialize:
                continue

            field_value = getattr(self, field.name, MISSING)
            if skip_none_field and field_value is None:
                continue

            if isinstance_safe(field_value, Declared):
                field_value = field_value.to_dict(skip_none_field)

            if field.serializer and enable_serializer:
                field_value = field.serializer.to_representation(field_value)

            result.append((field.field_name, field_value))

        return dict(result)

    @classmethod
    def from_form_data(cls, form_data):
        # type: (Type[_DT], str) -> _DT
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(urlparse.parse_qsl(form_data)), True)  # type: ignore

    def to_form_data(self, skip_none_field=False):
        # type: (bool) -> str
        if self.has_nest_declared_class():
            raise ValueError("can't serialize with nested declared class.")

        data = self.to_dict(skip_none_field, True)
        return "&".join([f"{k}={v}" for k, v in data.items()])

    @classmethod
    def from_query_string(cls, query_string):
        # type: (Type[_DT], str) -> _DT
        if cls.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        return cls.from_dict(dict(urlparse.parse_qsl(query_string)), True)  # type: ignore

    def to_query_string(
        self,
        skip_none_field=False,
        **urlkwargs,
    ):
        # type: (bool, Any) -> str
        if self.has_nest_declared_class():
            raise ValueError("can't deserialize to nested declared class.")

        data = self.to_dict(skip_none_field, True)
        return urlparse.urlencode(data, **urlkwargs)

    @overload
    def to_json(
        self,
        skipkeys: bool = ...,
        ensure_ascii: bool = ...,
        check_circular: bool = ...,
        allow_nan: bool = ...,
        cls: Optional[Type[JSONEncoder]] = ...,
        indent: Union[None, int, str] = ...,
        separators: Optional[Tuple[str, str]] = ...,
        default: Optional[Callable[[Any], Any]] = ...,
        sort_keys: bool = ...,
        skip_none_field: bool = ...,
        **kwds: Any,
    ) -> str:
        ...

    def to_json(self, skip_none_field=False, **kw):
        # type: (bool, Any) -> "str"
        return json.marshal(self, json.Options(skip_none_field, json_loads=kw))

    @overload
    @classmethod
    def from_json(
        cls_: Type[_DT],  # type: ignore
        s: JsonData,
        *,
        cls: Optional[Type[JSONDecoder]] = ...,
        object_hook: Optional[Callable[[Dict[Any, Any]], Any]] = ...,
        parse_float: Optional[Callable[[str], Any]] = ...,
        parse_int: Optional[Callable[[str], Any]] = ...,
        parse_constant: Optional[Callable[[str], Any]] = ...,
        object_pairs_hook: Optional[Callable[[List[Tuple[Any, Any]]], Any]] = ...,
        **kwds: Any,
    ) -> _DT:
        ...

    @classmethod
    def from_json(cls: Type[_DT], s: JsonData, **kw: Any) -> _DT:
        return json.unmarshal(cls, s, json.Options(json_dumps=kw))

    @classmethod
    def from_xml(cls: Type[_DT], element: ET.Element) -> _DT:
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
        return xml.unmarshal(cls, element, xml.Options())

    @classmethod
    def from_xml_string(cls: Type[_DT], xml_string: str) -> _DT:
        return cls.from_xml(ET.XML(xml_string))  # type: ignore

    def to_xml(self, skip_none_field=False, indent=None):
        # type: (bool, Optional[str]) -> ET.Element
        """
        <?xml version="1.0"?>
        <tag id="`id`" style="`style`">
            `text`
        </tag>
        """
        node = xml.marshal(self, xml.Options(skip_none_field, indent))
        if indent is not None:
            xml_prettify(node, indent, "\n")
        return node

    def to_xml_bytes(self, skip_none_field=False, indent=None, **kw) -> bytes:
        # type: (bool, Optional[str], Any) -> bytes
        return ET.tostring(self.to_xml(skip_none_field, indent), **kw)

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
        return f"{self.__class__.__name__}({', '.join(args)})"

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


def fields(class_or_instance: Union[Type[_DT], _DT]) -> Tuple[Var[Any, Any]]:
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
        var = meta_vars[f]
        out.append(var)
    return tuple(out)
