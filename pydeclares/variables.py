from abc import abstractmethod
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    SupportsBytes,
    SupportsComplex,
    SupportsFloat,
    SupportsInt,
    Text,
    Type,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Protocol, runtime_checkable

from pydeclares import declares
from pydeclares.utils import NamingStyle, isinstance_safe

_T = TypeVar("_T", bound="Var[Any, Any]")
_GT = TypeVar("_GT")
_ST = TypeVar("_ST")


class _UnicodeCodec(Generic[_GT], Protocol):
    def encode(self, _: _GT):
        ...

    def decode(self, _: Text) -> _GT:
        ...


@runtime_checkable
class _Castable(Generic[_GT], Protocol):
    @abstractmethod
    def cast(self) -> _GT:
        ...


class Var(Generic[_GT, _ST]):
    """a represantation of declared class member varaiable
    recommend use var function to create Var object, don't use this construct directly
    """

    def __init__(
        self,
        required: bool = True,
        field_name: Optional[str] = None,
        default: Optional[_GT] = None,
        default_factory: Optional[Callable[..., _GT]] = None,
        ignore_serialize: bool = False,
        naming_style: Callable[[str], str] = NamingStyle.snakecase,
        as_xml_attr: bool = False,
        as_xml_text: bool = False,
        init: bool = True,
        unicode_codec: Optional[_UnicodeCodec[_GT]] = None,
    ):
        """check input arguments and create a Var object

        Usage:
            >>> class NewClass(Declared):
            >>>     new_field = var(int)
            >>>     another_new_field = var(str, field_name="anf")

        :param type_: a type object, or a str object that express one class of imported or declared in later,
                    if use not declared or not imported class by string, a TypeError will occur in object
                    construct or set attribute to those objects.

        :param required: a bool object, constructor, this variable can't be missing in serialize when it is True.
                        on the other hand, this variable will be set None as default if `required` is False.

        :param field_name: a str object, use to serialize or deserialize custom field name.

        :param default: a Type[A] object, raise AttributeError when this field leak user input value but
                        this value is not instance of Type.

        :param default_factory: a callable object that can return a Type[A] object, as same as default parameter
                                but it is more flexible.

        :param naming_style: a callable object, that can change naming style without redefined field name by `field_name` variable

        :param as_xml_attr: a bool object, to declare one field as a xml attribute container

        :param as_xml_text: a bool object, to declare one field as a xml text container

        :param ignore_serialize: a bool object, if it is True then will omit in serialize.

        :param init: a bool object, the parameter determines whether this variable will be initialize by default initializer.
                    if it is False, then do not initialize with default initializer for this variable, and you must set attribute
                    in other place otherwise there are AttributeError raised in serializing.
        """
        self.name = ""
        self._field_name = field_name
        self.default = default
        self.default_factory = default_factory
        self.required = required
        self.init = init
        self.ignore_serialize = ignore_serialize
        self.naming_style = naming_style

        self.as_xml_attr = as_xml_attr
        self.as_xml_text = as_xml_text

        self.ucodec = unicode_codec

    @property
    def field_name(self):
        """ Cache handled field raw name """
        if self._field_name is None:
            self._field_name = self.naming_style(self.name)
        return self._field_name

    def make_default(self) -> Optional[_GT]:
        field_value = None
        if self.default is not None:
            field_value = self.default
        elif self.default_factory is not None:
            field_value = self.default_factory()

        if field_value is None:
            return field_value

        if not isinstance_safe(field_value, self.type_):
            return self.cast_it(field_value)

        return None

    @property
    @abstractmethod
    def type_(self) -> Type[_GT]:
        raise NotImplementedError

    @property
    @abstractmethod
    def construct(self) -> Callable[..., _GT]:
        raise NotImplementedError

    @abstractmethod
    def cast_it(self, obj: _ST) -> _GT:
        raise NotImplementedError

    @overload
    def __get__(self, instance: "declares.Declared", owner: Any) -> _GT:
        ...

    @overload
    def __get__(self: _T, instance: None, owner: Any) -> _T:
        ...

    @overload
    def __get__(self: _T, instance: Any, owner: Any) -> _T:
        ...

    def __get__(self, instance: Any, owner: Any):
        return getattr(instance, self.name)

    def __set__(self, instance: Any, value: _ST) -> None:
        if not isinstance(instance, self.type_):
            instance = self.cast_it(instance)
        setattr(instance, self.name, value)


class Int(Var[int, SupportsInt]):
    @property
    def type_(self):
        return int

    @property
    def construct(self):
        return int

    def cast_it(self, obj: SupportsInt) -> int:
        return int(obj)


class Float(Var[float, SupportsFloat]):
    @property
    def type_(self):
        return float

    @property
    def construct(self):
        return float

    def cast_it(self, obj: SupportsFloat) -> float:
        return float(obj)


class Complex(Var[complex, SupportsComplex]):
    @property
    def type_(self):
        return complex

    @property
    def construct(self):
        return complex

    def cast_it(self, obj: SupportsComplex) -> complex:
        return complex(obj)


class Bytes(Var[bytes, SupportsBytes]):
    @property
    def type_(self):
        return bytes

    @property
    def construct(self):
        return bytes

    def cast_it(self, obj: SupportsBytes) -> bytes:
        return bytes(obj)


class SupportsStr(Protocol):
    def __str__(self) -> Text:
        ...


class String(Var[str, SupportsStr]):
    @property
    def type_(self):
        return str

    @property
    def construct(self):
        return str

    def cast_it(self, obj: SupportsStr) -> Text:
        return str(obj)


class var(Var[_GT, _Castable[_GT]]):
    @overload
    def __init__(
        self,
        type_: Type[_GT],
        required: bool = ...,
        field_name: Optional[str] = ...,
        default: Optional[_GT] = ...,
        default_factory: Optional[Callable[..., _GT]] = ...,
        ignore_serialize: bool = ...,
        naming_style: Callable[[str], str] = ...,
        as_xml_attr: bool = ...,
        as_xml_text: bool = ...,
        init: bool = ...,
        unicode_codec: Optional[_UnicodeCodec[_GT]] = ...,
    ):
        ...

    def __init__(self, type_: Type[_GT], *args: Any, **kwargs: Any):
        self._type = type_
        super().__init__(*args, **kwargs)

    @property
    def type_(self):
        return self._type

    @property
    def construct(self):
        return self._type

    def cast_it(self, obj: _Castable[_GT]) -> _GT:
        try:
            return obj.cast()
        except AttributeError:
            raise TypeError(f"{obj.__class__} has not implemented protocol _Castable")


class _DeferedVar(Var[_GT, _ST]):
    @overload
    def __init__(
        self,
        type_: Type[_GT],
        required: bool = ...,
        field_name: Optional[str] = ...,
        default: Optional[_GT] = ...,
        default_factory: Optional[Callable[..., _GT]] = ...,
        ignore_serialize: bool = ...,
        naming_style: Callable[[str], str] = ...,
        as_xml_attr: bool = ...,
        as_xml_text: bool = ...,
        init: bool = ...,
        unicode_codec: Optional[_UnicodeCodec[_GT]] = ...,
    ):
        ...

    def __init__(self, type_: Type[_GT], *args: Any, **kwargs: Any):
        self._type = type_
        super().__init__(*args, **kwargs)


_K = TypeVar("_K")
_V = TypeVar("_V")


class kv(_DeferedVar[Mapping[_K, _V], _Castable[Mapping[_K, _V]]]):
    @property
    def type_(self) -> Type[Mapping[_K, _V]]:
        return Mapping  # type: ignore

    @property
    def construct(self) -> Type[Dict[_K, _V]]:
        return dict  # type: ignore

    def cast_it(self, obj: _Castable[Mapping[_K, _V]]) -> Mapping[_K, _V]:
        try:
            return obj.cast()
        except AttributeError:
            raise TypeError(f"{obj.__class__} has not implemented protocol _Castable")


class vec(_DeferedVar[List[_GT], _Castable[Iterable[_GT]]]):
    @property
    def type_(self) -> Type[List[_GT]]:
        return List  # type: ignore

    @property
    def construct(self) -> Type[List[_GT]]:
        return list  # type: ignore

    def cast_it(self, obj: _Castable[Iterable[_GT]]) -> List[_GT]:
        try:
            return list(obj.cast())
        except AttributeError:
            raise TypeError(f"{obj.__class__} has not implemented protocol _Castable")


@overload
def compatible_var(
    type_: Union[Type[_GT], "declares.GenericList[_GT]"],
    required: bool = ...,
    field_name: Optional[str] = ...,
    default: Optional[_GT] = ...,
    default_factory: Optional[Callable[..., _GT]] = ...,
    ignore_serialize: bool = ...,
    naming_style: Callable[[str], str] = ...,
    as_xml_attr: bool = ...,
    as_xml_text: bool = ...,
    init: bool = ...,
    unicode_codec: Optional[_UnicodeCodec[_GT]] = ...,
) -> Var[_GT, _Castable[_GT]]:
    ...


def compatible_var(
    type_: Union[Type[_T], "declares.GenericList[_T]"], *args: Any, **kwargs: Any
) -> Var[_GT, _ST]:
    if issubclass(type_, declares.GenericList):  # type: ignore
        return vec(type_.__type__, *args, **kwargs)  # type: ignore
    return var(type_, *args, **kwargs)  # type: ignore
