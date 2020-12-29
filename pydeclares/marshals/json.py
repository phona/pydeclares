import json
from collections import UserList, UserDict
from typing import Dict, Generic, List, Type, TypeVar, Union, overload
from typing_extensions import runtime_checkable

from typing_extensions import Protocol
from pydeclares import declares, variables
from pydeclares.defines import Json, JsonData, MISSING
from pydeclares.utils import isinstance_safe, issubclass_safe


_Literal = Union[str, int, float, bool, None]
_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


class MarshalError(Exception):
    ...


@runtime_checkable
class _UnMarshalable(Protocol):
    def to_json(self, options: "Options") -> str:
        ...


class Vec(Generic[_T], UserList):
    data: List[_T]

    def __init__(self, vec: "variables.vec"):
        self.vec = vec
        self.item_var = variables.compatible_var(vec.item_type)
        self.data = []

    def _marshal_item(self, item: Json, options: "Options"):
        v = _marshal_field(self.vec.item_type, self.item_var, item, options)
        if not self.item_var.type_checking(v):
            return self.item_var.cast_it(v)  # type: ignore
        return v

    def to_json(self, options: "Options") -> str:
        return json.dumps(
            [_unmarshal_field(self.vec.item_type, self.vec, i, options) for i in self]
        )

    def __str__(self):
        return str(self.data)


class KV(Generic[_K, _V], UserDict):
    data: Dict[_K, _V]

    def __init__(self, kv: "variables.kv"):
        self.kv = kv
        self.data = {}
        self.k_var = variables.compatible_var(kv.k_type)
        self.v_var = variables.compatible_var(kv.v_type)

    def _marshal_k_v(self, k: Json, v: Json, options: "Options"):
        k_ = _marshal_field(self.k_var, self.kv.k_type, k, options)
        v_ = _marshal_field(self.v_var, self.kv.v_type, v, options)
        if not self.k_var.type_checking(k_):
            k_ = self.k_var.cast_it(k_)  # type: ignore
        if not self.v_var.type_checking(v_):
            v_ = self.v_var.cast_it(v_)  # type: ignore
        return (k_, v_)

    def to_json(self, options: "Options"):
        return json.dumps(
            {
                _unmarshal_field(self.kv.k_type, self.kv, k, options): _unmarshal_field(
                    self.kv.k_type, self.kv, v, options
                )
                for k, v in self.items()
            }
        )

    def __str__(self):
        return str(self.data)


class Options:
    def __init__(self, encode_json=False, skip_none_field=False):
        self.encode_json = encode_json
        self.skip_none_field = skip_none_field


_DT = TypeVar("_DT", bound="declares.Declared")


@overload
def marshal(typ: Type[_DT], buf: JsonData, options: Options) -> _DT:
    ...


@overload
def marshal(typ: "variables.vec[_T]", buf: JsonData, options: Options) -> Vec[_T]:
    ...


@overload
def marshal(typ: "variables.kv[_K, _V]", buf: JsonData, options: Options) -> KV[_K, _V]:
    ...


def marshal(typ, buf: JsonData, options: Options):
    if isinstance(typ, variables.vec):
        li = json.loads(buf)
        assert isinstance(li, List)
        vec = Vec(typ)  # type: ignore
        vec.extend(
            map(
                lambda item: vec._marshal_item(item, options),
                li,
            )
        )
        return vec
    elif isinstance(typ, variables.kv):
        mapping = json.loads(buf)
        assert isinstance(mapping, Dict)
        kv = KV(typ)  # type: ignore
        kv.update(dict(map(lambda k, v: kv._marshal_k_v(k, v, options), mapping.items())))
        return kv

    return _marshal(typ, json.loads(buf), options)


def _marshal(marshalable, data: Json, options: Options):
    if isinstance_safe(marshalable, variables.vec):
        assert isinstance(data, List)
        return [
            _marshal_field(marshalable.item_type, marshalable, i, options) for i in data
        ]
    elif isinstance_safe(marshalable, variables.kv):
        assert isinstance(data, Dict)
        return {
            _marshal_field(marshalable.k_type, marshalable, k, options): _marshal_field(
                marshalable.v_type, marshalable, v, options
            )
            for k, v in data
        }
    elif issubclass_safe(marshalable, declares.Declared):
        assert isinstance(data, Dict)
        if not data:
            return marshalable()

        init_kwargs = {}
        for field in declares.fields(marshalable):
            field_value = data.get(field.field_name, MISSING)
            if field_value is MISSING:
                field_value = field.make_default()

            if field.type_checking(field_value):
                field_value = _marshal_field(field.type_, field, field_value, options)

            init_kwargs[field.name] = field_value

        return marshalable(**init_kwargs)
    elif isinstance_safe(marshalable, Json):
        return data

    raise MarshalError(f"type {marshalable} is not marshalable")


def _marshal_field(typ, field, value, options: Options):
    if issubclass(typ, _Literal.__args__):  # type: ignore
        return value
    elif issubclass_safe(typ, declares.Declared):
        return _marshal(typ, value, options)
    elif isinstance_safe(typ, List):
        assert isinstance(value, List)
        return [_marshal_field(field.item_type, field, i, options) for i in value]
    elif isinstance_safe(typ, Dict):
        assert isinstance(value, Dict)
        return {
            _marshal_field(field.k_type, field, k, options): _marshal_field(
                field.v_type, field, v, options
            )
            for k, v in value.items()
        }

    if not field.codec:
        raise MarshalError(f"can't marshal type {type(value)} to {typ}")

    return field.codec.decode(value)


def unmarshal(
    unmarshalable_or_declared: Union[_UnMarshalable, "declares.Declared"],
    options: Options,
) -> str:
    if isinstance(unmarshalable_or_declared, _UnMarshalable):
        return unmarshalable_or_declared.to_json(options)
    else:
        data = _unmarshal_declared(unmarshalable_or_declared, options)
        return json.dumps(data)


def _unmarshal_declared(
    declared: "declares.Declared", options: Options
) -> Dict[str, Json]:
    kv = {}
    for field in declares.fields(declared):
        kv[field.field_name] = _unmarshal_field(
            field.type_, field, getattr(declared, field.name), options
        )
    return kv


def _unmarshal_field(typ, field, value, options):
    if isinstance_safe(typ, declares.Declared):
        return _unmarshal_declared(value, options)
    elif isinstance_safe(typ, variables.vec):
        return [_unmarshal_field(field.item_type, field, v, options) for v in value]
    elif isinstance_safe(typ, variables.kv):
        return {
            _unmarshal_field(field.k_type, field, k, options): _unmarshal_field(
                field.v_type, field, v, options
            )
            for k, v in value.items()
        }
    elif issubclass(typ, _Literal.__args__):  # type: ignore
        return value

    if not field.codec:
        raise MarshalError(f"can't unmarshal type {type(value)}")

    return field.codec.encode(value)
