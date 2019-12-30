WALTZ_VERSION = '0.1.0'

REGISTRY_PATH = "settings/registry.yaml"

DEFAULT_SERVICES = {}


def register_default_service(service: 'Service'):
    """
    Includes the given Service as a default

    Args:
        service (Service): The actual service entity
        constructor (... -> Service): The constructor for this service
    """
    DEFAULT_SERVICES[service.name] = service


def get_default_services():
    return DEFAULT_SERVICES.copy()
