from functools import partial

from pydeclares.variables import var, NamingStyle
from pydeclares.declares import Declared, new_list_type as GenericList
from pydeclares.codecs import as_codec


pascalcase_var = partial(var, naming_style=NamingStyle.pascalcase)
camelcase_var = partial(var, naming_style=NamingStyle.camelcase)
