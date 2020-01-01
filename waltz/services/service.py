from waltz.exceptions import WaltzException


class Service:
    """
    Services can either be Abstract, Generic, or Specific. The Abstract courses are the ones configured
    to be instantiated within Waltz as either Generic or Specific. The Generic Services allow you to
    use them without reference to a Course. The Specific ones can override settings in order to have further
    specifications.
    """
    RESOURCES: 'Dict[str, Resource]'
    name: str
    # The service that this one extends; if None, then this is an Abstract service
    parent: str
    settings: dict
    default: bool

    def __init__(self, name: str, parent: str, settings: dict, default=False):
        self.name = name
        self.parent = parent
        self.default = default
        self.settings = settings

    @classmethod
    def register_resource(cls, resource_category):
        for name in resource_category.category_names:
            cls.RESOURCES[name] = resource_category

    def as_data(self):
        return {
            'name': self.name,
            'parent': self.parent,
            'settings': self.settings
        }

    @classmethod
    def from_data(cls, data, existing_services):
        name = data['name']
        parent = data['parent']
        # TODO: I flipped the order of these, but I think that's wrong. Need to approach when clear-headed
        #       Issue is that the course version of local should clobber the parent, but is that an exception?
        # Create a new version of this
        if parent in existing_services:
            old_version = existing_services[parent]
            constructor = type(old_version)
            old_settings = old_version.settings.copy()
            old_settings.update(data['settings'])
            return constructor(name, parent, old_settings)
        # Use the existing version
        if name in existing_services:
            return existing_services[name]

        raise WaltzException("Unknown parent service '{}' for service '{}'".format(parent, name))

    def copy(self, updates):
        pass

    def add_parser_copy(self, parser):
        pass

    def search(self, category, resource):
        return []


def services_as_data(services):
    return {name: service.as_data() for name, service in services.items()
            if not service.default}


def services_from_data(services, existing_services):
    return {name: Service.from_data(service, existing_services) for name, service in services.items()}