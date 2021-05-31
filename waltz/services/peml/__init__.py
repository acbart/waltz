from waltz.resources.peml_assignment import PemlAssignment
from waltz.defaults import register_service_type
from waltz.services.peml.peml import PEML


PEML.register_resource(PemlAssignment)

register_service_type(PEML)