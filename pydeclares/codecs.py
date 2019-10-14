from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from pydeclares.utils import isinstance_safe

_CODECS = {}


class CodecNotFoundError(Exception):
    """"""


def encode(inst):
    try:
        return _CODECS[type(inst)].encode(inst)
    except KeyError or AttributeError:
        raise CodecNotFoundError(f"Encoder of {type(inst)!r} is not found")


def decode(T, inst):
    try:
        return _CODECS[T].decode(inst)
    except KeyError or AttributeError:
        raise CodecNotFoundError(f"Decoder of {T!r} is not found")


def as_codec(T):
    def wrapped(cls):
        _CODECS[T] = cls
        return cls

    return wrapped


@as_codec(datetime)
class DatetimeCodec:
    @classmethod
    def encode(cls, inst):
        return inst.timestamp()

    @classmethod
    def decode(cls, inst):
        if isinstance_safe(inst, datetime):
            return inst
        else:
            tz = datetime.now(timezone.utc).astimezone().tzinfo
            return datetime.fromtimestamp(inst, tz=tz)


@as_codec(UUID)
class UUIDCodec:
    @classmethod
    def encode(cls, inst):
        return str(UUID)

    @classmethod
    def decode(cls, inst):
        return UUID(inst)


@as_codec(Enum)
class EnumCodec:
    @classmethod
    def encode(cls, inst):
        return inst.value
