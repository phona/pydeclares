from functools import partial

from pydeclares.declares import Declared
from pydeclares.variables import NamingStyle, compatible_var, vec

var = compatible_var
pascalcase_var = partial(var, naming_style=NamingStyle.pascalcase)
camelcase_var = partial(var, naming_style=NamingStyle.camelcase)

version = "1.0.0"

__all__ = [
    "Declared",
    "vec",
    "NamingStyle",
    "var",
    "pascalcase_var",
    "camelcase_var",
    "version",
]
