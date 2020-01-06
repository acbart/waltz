from typing import Type

WALTZ_VERSION = '0.1.0'

WALTZ_REGISTRY_FILE_NAME = ".waltz"
WALTZ_DATABASE_FILE_NAME = ".waltz.db"

SERVICE_TYPES = {}
RESOURCE_CATEGORIES = {}


def register_service_type(service: 'Type[Service]'):
    """
    Includes the given Service as a default

    Args:
        service (Service): The actual service entity
        constructor (... -> Service): The constructor for this service
    """
    SERVICE_TYPES[service.type] = service
    for name, Resource in service.RESOURCES.items():
        RESOURCE_CATEGORIES[name] = Resource


def get_service_types():
    return SERVICE_TYPES.copy()


def get_resource_categories():
    return RESOURCE_CATEGORIES.copy()
