from waltz.exceptions import WaltzException
from waltz.defaults import get_service_types


class Service:
    """
    Services can either be Abstract, Generic, or Specific. The Abstract courses are the ones configured
    to be instantiated within Waltz as either Generic or Specific. The Generic Services allow you to
    use them without reference to a Course. The Specific ones can override settings in order to have further
    specifications.
    """
    RESOURCES: 'Dict[str, Resource]'
    name: str
    type: str
    # The service that this one extends; if None, then this is an Abstract service
    settings: dict

    def __init__(self, name: str, settings: dict):
        self.name = name
        self.settings = settings

    @classmethod
    def from_type(cls, service_type: str):
        return get_service_types()[service_type]

    @classmethod
    def register_resource(cls, resource_category):
        for name in resource_category.category_names:
            cls.RESOURCES[name] = resource_category

    @classmethod
    def get_resource_base(cls, resource_category):
        return cls.RESOURCES[resource_category]

    def as_data(self):
        return {
            'name': self.name,
            'type': self.type,
            'settings': self.settings
        }

    @classmethod
    def from_data(cls, data):
        name = data['name']
        settings = data['settings']
        return cls(name, settings)

    def service_type(self, parser):
        pass

    def search(self, category, resource):
        return []

    @classmethod
    def add_parser_download(cls, parser):
        return parser


def services_as_data(services_types):
    return {name: [service.as_data() for service in services]
            for name, services in services_types.items()}


def services_from_data(services_by_type, service_types):
    return {name: [service_types[service['type']].from_data(service)
                   for service in services]
            for name, services in services_by_type.items()}
