import inspect
from xml.etree.ElementTree import Element


def tuple_str(obj_name, fields):
    # Return a string representing each field of obj_name as a tuple
    # member.  So, if fields is ['x', 'y'] and obj_name is "self",
    # return "(self.x,self.y)".

    # Special case for the 0-tuple.
    if not fields:
        return '()'
    # Note the trailing comma, needed if this turns out to be a 1-tuple.
    return f'({",".join([f"{obj_name}.{f.name}" for f in fields])},)'


def isinstance_safe(o, t):
    try:
        result = isinstance(o, t)
    except Exception:
        return False
    else:
        return result


def issubclass_safe(cls, classinfo):
    try:
        return issubclass(cls, classinfo)
    except Exception:
        return (is_new_type_subclass_safe(cls, classinfo) if is_new_type(cls) else False)


def is_new_type_subclass_safe(cls, classinfo):
    super_type = getattr(cls, "__supertype__", None)

    if super_type:
        return is_new_type_subclass_safe(super_type, classinfo)

    try:
        return issubclass(cls, classinfo)
    except Exception:
        return False


def is_new_type(type_):
    return inspect.isfunction(type_) and hasattr(type_, "__supertype__")


def xml_prettify(element: Element, indent: str, newline: str = '\n', level: int = 0) -> None:
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
