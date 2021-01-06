from typing import Union

Json = Union[dict, list, str, int, float, bool, None]
JsonData = Union[str, bytes, bytearray]


class _MISSING_TYPE:
    def __str__(self):
        return "MISSING"


MISSING = _MISSING_TYPE()
