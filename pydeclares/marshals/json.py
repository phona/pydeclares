import json
from collections import UserDict, UserList
from typing import Dict, Generic, List, Optional, Type, TypeVar, Union, overload

from pydeclares import declares, variables
from pydeclares.defines import MISSING, Json, JsonData
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.utils import isinstance_safe, issubclass_safe
from typing_extensions import Protocol, runtime_checkable

_Literal = Union[str, int, float, bool, None]
_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


@runtime_checkable
class _Marshalable(Protocol):
    def marshal(self, options: "Options") -> str:
        ...


class Vec(Generic[_T], UserList):
    data: List[_T]

    def __init__(self, vec: "variables.vec"):
        self.vec = vec
        self.item_var = variables.compatible_var(vec.item_type)
        self.data = []

    def _unmarshal_item(self, item: Json, options: "Options"):
        v = _unmarshal_field(self.vec.item_type, self.item_var, item, options)
        if not self.item_var.type_checking(v):
            return self.item_var.cast_it(v)  # type: ignore
        return v

    def marshal(self, options: "Options") -> str:
        return json.dumps(
            [_marshal_field(self.vec.item_type, self.vec, i, options) for i in self],
            **options.json_dumps,
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

    def _unmarshal_k_v(self, k: Json, v: Json, options: "Options"):
        k_ = _unmarshal_field(self.kv.k_type, self.k_var, k, options)
        v_ = _unmarshal_field(self.kv.v_type, self.v_var, v, options)
        if not self.k_var.type_checking(k_):
            k_ = self.k_var.cast_it(k_)  # type: ignore
        if not self.v_var.type_checking(v_):
            v_ = self.v_var.cast_it(v_)  # type: ignore
        return (k_, v_)

    def marshal(self, options: "Options"):
        return json.dumps(
            {
                _marshal_field(self.kv.k_type, self.kv, k, options): _marshal_field(
                    self.kv.v_type, self.kv, v, options
                )
                for k, v in self.items()
            },
            **options.json_dumps,
        )

    def __str__(self):
        return str(self.data)


class Options:
    def __init__(self, skip_none_field=False, json_loads={}, json_dumps={}):
        self.skip_none_field = skip_none_field
        self.json_loads = json_loads
        self.json_dumps = json_dumps


_DT = TypeVar("_DT", bound="declares.Declared")


_default_options = Options()


@overload
def unmarshal(typ, buf, options=...):
    # type: (Type[_DT], JsonData, Options) -> _DT
    ...


@overload
def unmarshal(typ, buf, options=...):
    # type: (variables.vec[_T], JsonData, Options) -> Vec[_T]
    ...


@overload
def unmarshal(typ, buf, options=...):
    # type: (variables.kv[_K, _V], JsonData, Options) -> KV[_K, _V]
    ...


def unmarshal(typ, buf: JsonData, options: Options = _default_options):
    if isinstance(typ, variables.vec):
        li = json.loads(buf, **options.json_loads)
        assert isinstance(li, List)
        vec = Vec(typ)  # type: ignore
        vec.extend(
            map(
                lambda item: vec._unmarshal_item(item, options),
                li,
            )
        )
        return vec
    elif isinstance(typ, variables.kv):
        mapping = json.loads(buf, **options.json_loads)
        assert isinstance(mapping, Dict)
        kv = KV(typ)  # type: ignore
        kv.update(
            dict(
                map(
                    lambda tup: kv._unmarshal_k_v(tup[0], tup[1], options),
                    mapping.items(),
                )
            )
        )
        return kv

    return _unmarshal(typ, json.loads(buf, **options.json_loads), options)


def _unmarshal(marshalable, data: Json, options: Options):
    if isinstance_safe(marshalable, variables.vec):
        assert isinstance(data, List)
        return [
            _unmarshal_field(marshalable.item_type, marshalable, i, options)
            for i in data
        ]
    elif isinstance_safe(marshalable, variables.kv):
        assert isinstance(data, Dict)
        return {
            _unmarshal_field(
                marshalable.k_type, marshalable, k, options
            ): _unmarshal_field(marshalable.v_type, marshalable, v, options)
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

            if not field.type_checking(field_value):
                field_value = _unmarshal_field(field.type_, field, field_value, options)

            init_kwargs[field.name] = field_value

        return marshalable(**init_kwargs)
    elif isinstance_safe(marshalable, Json):
        return data

    raise MarshalError(f"type {marshalable} is not unmarshalable")


def _unmarshal_field(typ, field, value, options: Options):
    if issubclass_safe(typ, _Literal.__args__):  # type: ignore
        return value
    elif issubclass_safe(typ, declares.Declared):
        return _unmarshal(typ, value, options)
    elif isinstance_safe(typ, List):
        assert isinstance(value, List)
        return [_unmarshal_field(field.item_type, field, i, options) for i in value]
    elif isinstance_safe(typ, Dict):
        assert isinstance(value, Dict)
        return {
            _unmarshal_field(field.k_type, field, k, options): _unmarshal_field(
                field.v_type, field, v, options
            )
            for k, v in value.items()
        }

    if not field.codec:
        raise MarshalError(
            f"can't unmarshal {type(value)!r} to property {field.name} which are {typ!r}"
        )

    return field.codec.decode(value)


def marshal(
    unmarshalable_or_declared: Union[_Marshalable, "declares.Declared"],
    options: Options = _default_options,
) -> str:
    if isinstance(unmarshalable_or_declared, declares.Declared):
        data = _marshal_declared(unmarshalable_or_declared, options)
        return json.dumps(data, **options.json_dumps)
    else:
        return unmarshalable_or_declared.marshal(options)


def _marshal_declared(
    declared: "declares.Declared", options: Options
) -> Dict[str, Json]:
    kv = {}
    for field in declares.fields(declared):
        kv[field.field_name] = _marshal_field(
            field.type_, field, getattr(declared, field.name), options
        )
    return kv


def _marshal_field(typ, field, value, options):
    if issubclass_safe(typ, declares.Declared):
        return _marshal_declared(value, options)
    elif issubclass_safe(typ, List):
        return [_marshal_field(field.item_type, field, v, options) for v in value]
    elif issubclass_safe(typ, Dict):
        return {
            _marshal_field(field.k_type, field, k, options): _marshal_field(
                field.v_type, field, v, options
            )
            for k, v in value.items()
        }
    elif issubclass_safe(typ, _Literal.__args__):  # type: ignore
        return value

    if not field.codec:
        raise MarshalError(f"can't marshal property {field.name} which are {typ!r}")

    return field.codec.encode(value)
