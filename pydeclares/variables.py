import re

from pydeclares.defines import _REGISTER_DECLARED_CLASS, MISSING
from pydeclares.utils import isinstance_safe


class NamingStyle:
    """ reference to python-stringcase

    https://github.com/okunishinishi/python-stringcase
    """

    @classmethod
    def camelcase(cls, string):
        string = re.sub(r"^[\-_\.]", '', str(string))
        if not string:
            return string
        return string[0].lower() + re.sub(r"[\-_\.\s]([a-z])", lambda matched: (matched.group(1)).upper(), string[1:])

    @classmethod
    def snakecase(cls, string):
        string = re.sub(r"[\-\.\s]", '_', str(string))
        if not string:
            return string
        return string[0].lower() + re.sub(r"[A-Z]", lambda matched: '_' + (matched.group(0)).lower(), string[1:])

    @classmethod
    def pascalcase(cls, string):
        string = cls.camelcase(string)
        if not string:
            return string
        return string[0].upper() + string[1:]


class Var:
    """ a represantation of declared class member varaiable
    recommend use var function to create Var object, don't use this construct directly
    """

    def __init__(self,
                 type_,
                 required=True,
                 field_name=MISSING,
                 default=MISSING,
                 default_factory=MISSING,
                 ignore_serialize=False,
                 naming_style=NamingStyle.snakecase,
                 as_xml_attr=False,
                 as_xml_text=False,
                 auto_cast=True,
                 init=True):
        self._type = type_
        self.name = ""
        self._field_name = field_name
        self.default = default
        self.default_factory = default_factory
        self.required = required
        self.init = init
        self.ignore_serialize = ignore_serialize
        self.naming_style = naming_style
        self.auto_cast = auto_cast

        self.as_xml_attr = as_xml_attr
        self.as_xml_text = as_xml_text

    @property
    def field_name(self):
        """ Cache handled field raw name """
        if self._field_name is MISSING:
            self._field_name = self.naming_style(self.name)
        return self._field_name

    @property
    def type_(self):
        if type(self._type) is str:
            self._type = _REGISTER_DECLARED_CLASS[self._type]
        return self._type

    def make_default(self):
        field_value = MISSING
        if self.default is not MISSING:
            field_value = self.default
        elif self.default_factory is not MISSING:
            field_value = self.default_factory()

        if self.check(field_value):
            return field_value
        return MISSING

    def check(self, obj):
        if obj is MISSING or obj is None:
            return True
        type_ = self.type_
        if getattr(type_, "__origin__", None):
            type_ = type_.__origin__

        if not isinstance_safe(obj, type_):
            raise TypeError("%r is not a instance of %r" % (type(obj).__name__, self.type_.__name__))
        return True


def var(type_,
        required=True,
        field_name=MISSING,
        default=MISSING,
        default_factory=MISSING,
        ignore_serialize=False,
        naming_style=NamingStyle.snakecase,
        as_xml_attr=False,
        as_xml_text=False,
        auto_cast=True,
        init=True):
    """ check input arguments and create a Var object

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
    if default is not MISSING and default_factory is not MISSING:
        raise ValueError('cannot specify both default and default_factory')
    return Var(type_, required, field_name, default, default_factory, ignore_serialize, naming_style, as_xml_attr,
               as_xml_text, auto_cast, init)
