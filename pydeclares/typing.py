try:
    from typing import Literal, Protocol, overload, runtime_checkable  # type: ignore
except ImportError:
    from typing_extensions import Literal, Protocol, overload, runtime_checkable  # type: ignore


__all__ = ["Literal", "Protocol", "runtime_checkable", "overload"]
