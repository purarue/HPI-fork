"""
This is here temporarily, for backwards compatibility purposes
It should be removed in the future, and you should replace any imports
like:
from my.fbmessenger import ...
to:
from my.fbmessenger.all import ...
since that allows for easier overriding using namespace packages
See https://github.com/karlicoss/HPI/blob/master/doc/MODULE_DESIGN.org#allpy for more info.
"""

# prevent it from appearing in modules list/doctor
from my.core import __NOT_HPI_MODULE__  # noqa: F401  # isort: skip

# kinda annoying to keep it, but it's so legacy 'hpi module install my.fbmessenger' works
# needs to be on the top level (since it's extracted via ast module)
REQUIRES = [
    'fbmessengerexport @ git+https://github.com/karlicoss/fbmessengerexport',
]


from my.core.hpi_compat import handle_legacy_import

is_legacy_import = handle_legacy_import(
    parent_module_name=__name__,
    legacy_submodule_name='export',
    parent_module_path=__path__,
)

if is_legacy_import:
    # todo not sure if possible to move this into legacy.py
    from .export import *

