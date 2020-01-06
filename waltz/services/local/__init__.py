from waltz import defaults
from waltz.resources.page import Page
from waltz.services.local.local import Local

Local.register_resource(Page)

defaults.register_service_type(Local)
