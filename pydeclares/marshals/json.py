import json
from collections import UserDict, UserList
from typing import Any, Dict, List, Type, TypeVar, Union, overload

from pydeclares import declares, variables
from pydeclares.defines import MISSING, Json, JsonData
from pydeclares.marshals.exceptions import MarshalError
from pydeclares.typing import Protocol, runtime_checkable
from pydeclares.utils import issubclass_safe

_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")


@runtime_checkable
class _Marshalable(Protocol):
    def marshal(self, options: "Options") -> str:
        ...


class Vec(List[_T], UserList):
    def __init__(self, vec: "variables.vec"):
        self.vec = vec
        self.item_var = variables.compatible_var(vec.item_type)

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


class KV(Dict[_K, _V], UserDict):
    def __init__(self, kv: "variables.kv"):
        self.kv = kv
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
                _marshal_field(self.kv.k_type, self.kv, k, options): _marshal_field(self.kv.v_type, self.kv, v, options)
                for k, v in self.items()
            },
            **options.json_dumps,
        )


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
    # type: (Type[declares.Declared], Json, Options) -> declares.Declared
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


def _unmarshal_field(typ, field, value, options: Options):
    # type: (type, Union[variables.Var, variables.vec, variables.kv], Any, Options) -> Any
    if value is None:
        return None
    elif issubclass(typ, declares.Declared):
        return _unmarshal(typ, value, options)
    elif issubclass(typ, List):
        assert isinstance(value, List) and isinstance(field, variables.vec)
        return [_unmarshal_field(field.item_type, field, i, options) for i in value]
    elif issubclass(typ, Dict):
        assert isinstance(value, Dict) and isinstance(field, variables.kv)
        return {
            _unmarshal_field(field.k_type, field, k, options): _unmarshal_field(field.v_type, field, v, options)
            for k, v in value.items()
        }

    if field.serializer:
        value = field.serializer.to_internal_value(value)

    return value


def marshal(
    unmarshalable_or_declared: Union[_Marshalable, "declares.Declared"],
    options: Options = _default_options,
) -> str:
    if isinstance(unmarshalable_or_declared, declares.Declared):
        data = _marshal_declared(unmarshalable_or_declared, options)
        return json.dumps(data, **options.json_dumps)
    else:
        return unmarshalable_or_declared.marshal(options)


def _marshal_declared(declared: "declares.Declared", options: Options) -> Dict[str, Json]:
    kv = {}
    for field in declares.fields(declared):
        if field.ignore_serialize:
            continue

        value = _marshal_field(field.type_, field, getattr(declared, field.name), options)
        if value is None and options.skip_none_field:
            continue

        kv[field.field_name] = value
    return kv


def _marshal_field(typ, field, value, options):
    if value is None:
        return None
    elif issubclass_safe(typ, declares.Declared):
        return _marshal_declared(value, options)
    elif issubclass_safe(typ, List):
        return [_marshal_field(field.item_type, field, v, options) for v in value]
    elif issubclass_safe(typ, Dict):
        return {
            _marshal_field(field.k_type, field, k, options): _marshal_field(field.v_type, field, v, options)
            for k, v in value.items()
        }

    if field.serializer:
        value = field.serializer.to_representation(value)

    if not isinstance(value, Json.__args__):  # type: ignore
        raise MarshalError(f"can't marshal property `{field.name}` which are `{typ!r}`")

    return value
