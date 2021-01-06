import inspect
import re
from typing import Any, Tuple, Union, overload
from xml.etree.ElementTree import Element


@overload
def isinstance_safe(o: Any, _class_or_tuple: Union[type, Tuple[Union[type, Tuple[Any, ...]], ...]]) -> bool:
    ...


def isinstance_safe(o: Any, t: type):
    try:
        result = isinstance(o, t)
    except Exception:
        return False
    else:
        return result


@overload
def issubclass_safe(cls: type, _class_or_tuple: Union[type, Tuple[Union[type, Tuple[Any, ...]], ...]]) -> bool:
    ...


def issubclass_safe(cls: type, _class_or_tuple: type) -> bool:
    try:
        return issubclass(cls, _class_or_tuple)
    except Exception:
        return is_new_type_subclass_safe(cls, _class_or_tuple) if is_new_type(cls) else False


def is_new_type_subclass_safe(cls: type, classinfo: type) -> bool:
    super_type = getattr(cls, "__supertype__", None)

    if super_type:
        return is_new_type_subclass_safe(super_type, classinfo)

    try:
        return issubclass(cls, classinfo)
    except Exception:
        return False


def is_new_type(type_: type):
    return inspect.isfunction(type_) and hasattr(type_, "__supertype__")


def xml_prettify(element: Element, indent: str, newline: str = "\n", level: int = 0) -> None:
    """
    :params element:
    :params indent:
    :params newline:
    :params level:
    :return:
    """
    if element:
        if (element.text is None) or element.text.isspace():
            element.text = newline + indent * (level + 1)
        else:
            element.text = newline + indent * (level + 1) + element.text.strip() + newline + indent * (level + 1)
    temp = list(element)
    for subelement in list(element):
        if temp.index(subelement) < (len(temp) - 1):  # 如果不是list的最后一个元素，说明下一个行是同级别元素的起始，缩进应一致
            subelement.tail = newline + indent * (level + 1)
        else:  # 如果是list的最后一个元素， 说明下一行是母元素的结束，缩进应该少一个
            subelement.tail = newline + indent * level
        xml_prettify(subelement, indent, newline, level=level + 1)  # 对子元素进行递归操作


class NamingStyle:
    """reference to python-stringcase

    https://github.com/okunishinishi/python-stringcase
    """

    @classmethod
    def camelcase(cls, string: str):
        string = re.sub(r"^[\-_\.]", "", str(string))
        if not string:
            return string
        return string[0].lower() + re.sub(r"[\-_\.\s]([a-z])", lambda matched: (matched.group(1)).upper(), string[1:])

    @classmethod
    def snakecase(cls, string: str):
        string = re.sub(r"[\-\.\s]", "_", str(string))
        if not string:
            return string
        return string[0].lower() + re.sub(r"[A-Z]", lambda matched: "_" + (matched.group(0)).lower(), string[1:])

    @classmethod
    def pascalcase(cls, string: str):
        string = cls.camelcase(string)
        if not string:
            return string
        return string[0].upper() + string[1:]
