from functools import partial

from pydeclares.codecs import as_codec
from pydeclares.declares import Declared
from pydeclares.declares import new_list_type as GenericList
from pydeclares.variables import NamingStyle, var

pascalcase_var = partial(var, naming_style=NamingStyle.pascalcase)
camelcase_var = partial(var, naming_style=NamingStyle.camelcase)
