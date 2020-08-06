import gc
import logging
import os
import sqlite3
from typing import Type

from waltz import defaults as defaults
from waltz.exceptions import WaltzException, WaltzServiceNotFound, WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.resources.raw import RawResource
from waltz.services.service import services_from_data, services_as_data
from waltz.tools.yaml_setup import yaml


class Registry:
    """
    A collection of available courses and default services.
    """
    services: 'Dict[str, Service]'
    db: sqlite3.Connection
    directory: str
    version: str

    def __init__(self, directory, db, services, version):
        self.directory = directory
        self.db = db
        self.services = services
        self.version = version

    @classmethod
    def get_waltz_registry_path(cls, directory):
        return os.path.join(directory, defaults.WALTZ_REGISTRY_FILE_NAME)

    @classmethod
    def get_waltz_database_path(cls, directory):
        return os.path.join(directory, defaults.WALTZ_DATABASE_FILE_NAME)

    @classmethod
    def make_default(cls, directory) -> 'Registry':
        db = sqlite3.connect(cls.get_waltz_database_path(directory))
        services = {name: [] for name in defaults.get_service_types()}
        new_registry = Registry(directory=directory,
                        db=db,
                        services=services,
                        version=defaults.WALTZ_VERSION)
        new_registry.create_database()
        return new_registry

    @classmethod
    def load_version_010(cls, directory, data) -> 'Registry':
        db = sqlite3.connect(cls.get_waltz_database_path(directory))
        services = services_from_data(data['services'], defaults.get_service_types())
        return Registry(directory=directory,
                        db=db,
                        services=services,
                        version=data['version'])

    @classmethod
    def exists(cls, directory):
        registry_exists = os.path.exists(cls.get_waltz_registry_path(directory))
        database_exists = os.path.exists(cls.get_waltz_database_path(directory))
        if registry_exists and not database_exists:
            logging.warning("Registry exists but database ({}) is missing".format(defaults.WALTZ_DATABASE_FILE_NAME))
        if not registry_exists and database_exists:
            logging.warning("Database exists but registry ({}) is missing".format(defaults.WALTZ_REGISTRY_FILE_NAME))
        return registry_exists and database_exists

    @classmethod
    def delete(cls, directory):
        os.remove(cls.get_waltz_registry_path(directory))
        os.remove(cls.get_waltz_database_path(directory))

    @classmethod
    def init(cls, directory):
        os.makedirs(directory, exist_ok=True)
        return cls.make_default(directory).save_to_file()

    @classmethod
    def search_up_for_waltz_registry(cls, directory):
        while True:
            parent_directory = os.path.dirname(os.path.abspath(directory))
            if os.path.exists(cls.get_waltz_registry_path(directory)):
                return directory
            if parent_directory == directory:
                return None
            directory = parent_directory

    @classmethod
    def load(cls, directory, create_if_not_exists=True):
        directory = cls.search_up_for_waltz_registry(directory)
        if directory is not None:
            with open(cls.get_waltz_registry_path(directory)) as registry_file:
                registry_data = yaml.load(registry_file)
            version = registry_data['version']
            if version in ('0.1.0', ):
                return Registry.load_version_010(directory, registry_data)
            else:
                raise WaltzException("Unknown registry file version: {}\nMy version is: {}".format(
                    version, defaults.WALTZ_VERSION))
        elif create_if_not_exists:
            # TODO: default was specified? What does that mean.
            logging.warning("No registry file was detected; since default was specified, I'll create it instead.")
            # TODO: directory is None, indicating we didn't find the waltz file. Build it here?
            return Registry.init(directory)

    def save_to_file(self):
        registry_path = self.get_waltz_registry_path(self.directory)
        with open(registry_path, 'w') as registry_file:
            yaml.dump({
                'version': self.version,
                'services': services_as_data(self.services),
            }, registry_file)
        return self

    def create_database(self):
        self.db.execute("CREATE TABLE resources (service text, category text, title text, disambiguate text, data text)")
        self.db.execute("CREATE UNIQUE INDEX idx_resource ON resources(service, category, title, disambiguate)")
        self.db.commit()

    def reset_database(self):
        self.db.close()
        waltz_database_path = self.get_waltz_database_path(self.directory)
        # TODO: Are these still necessary? My gut says no.
        # del self.db
        # import gc
        # gc.collect()
        os.remove(waltz_database_path)
        self.db = sqlite3.connect(waltz_database_path)
        self.create_database()

    def store_resource(self, service, category, title, disambiguate, resource_data):
        # TODO: Replace existing
        self.db.execute("REPLACE INTO resources VALUES (?, ?, ?, ?, ?)",
                        (service, category, title, disambiguate, resource_data))
        self.db.commit()

    def find_all_resources(self, service=None, category=None):
        resources = self.db.execute("SELECT service, category, title, disambiguate, data FROM resources "
                                    "WHERE service = ? AND category = ?", (service, category))
        return [RawResource.from_database(result) for result in resources.fetchall()]

    def find_resource(self, service=None, category=None, title=None, disambiguate=None):
        parameters = {"service = ?": service, "category = ?": category,
                      "title = ?": title, "disambiguate = ?": disambiguate}
        terms = {column: term for column, term in parameters.items() if term is not None}
        resources = self.db.execute("SELECT service, category, title, disambiguate, data FROM resources "
                                    "WHERE {}".format(" AND ".join(terms.keys())), tuple(terms.values()))
        results = resources.fetchall()
        if resources.rowcount > 1:
            raise WaltzAmbiguousResource(
                "Ambiguous resource {}, found {} versions".format(" ".join(terms.values()), resources.rowcount),
                results
            )
        elif not results or not resources.rowcount:
            raise WaltzResourceNotFound("Could not find resource {}.".format(" ".join(map(str, terms.values()))))
        else:
            return RawResource.from_database(results[0])

    def configure_service(self, service):
        self.services[service.type].append(service)

    def get_service(self, name, default_name=None):
        if name is None:
            name = default_name
        if name in self.services:
            if not self.services[name]:
                raise WaltzException("Service {} is not configured".format(name))
            return self.services[name][0]
        for _, services in self.services.items():
            for service in services:
                if service.name == name:
                    return service
        raise WaltzServiceNotFound("Unknown service: {}".format(name))

    @classmethod
    def get_resource_category(cls, name: str):
        categories = defaults.get_resource_categories()
        if name in categories:
            return categories[name]
        raise WaltzResourceNotFound("Unknown resource category: {}".format(name))

    @classmethod
    def fill_args(cls, args, raw_resource):
        if args.service is None:
            args.service = raw_resource.service
        if args.category is None:
            args.category = raw_resource.category
        if args.title is None:
            args.title = raw_resource.title

    def guess_resource_category(self, args, arbitrary_service_order=None) -> 'Type[Resource]':
        """

        Args:
            args: This parameter will be modified.

        Returns:

        """
        # Build up general search terms
        search_terms = {}
        if args.id and args.url:
            raise WaltzAmbiguousResource("Ambiguous resource, can't use ID and URL for same search.")
        elif args.id:
            search_terms['disambiguate'] = args.id
        elif args.url:
            search_terms['disambiguate'] = args.url
        # Infer based on number of arguments
        if len(args.resource) == 0:
            if args.all:
                # TODO: Handle requesting all resources
                return None
            elif not args.id and not args.url:
                raise WaltzAmbiguousResource("Ambiguous resource, specify a resource title.")
            else:
                raw_resource = self.find_resource(**search_terms)
                self.fill_args(args, raw_resource)
                return self.get_resource_category(raw_resource.category)
        elif len(args.resource) == 1:
            # Is it just a service? (Better have --all or --id)
            try:
                service = self.get_service(args.resource[0])
                search_terms['service'] = service.name
                raw_resource = self.find_resource(**search_terms)
                self.fill_args(args, raw_resource)
                return self.get_resource_category(raw_resource.category)
            except WaltzServiceNotFound:
                pass
            # Is it just a category? (Better have --all or --id)
            try:
                category = self.get_resource_category(args.resource[0])
                search_terms['category'] = category.name
                raw_resource = self.find_resource(**search_terms)
                self.fill_args(args, raw_resource)
                return category
            except WaltzResourceNotFound:
                pass
            # Else, it is just a resource title. Do we know about it locally?
            search_terms['title'] = args.resource[0]
            raw_resource = self.find_resource(**search_terms)
            self.fill_args(args, raw_resource)
            return self.get_resource_category(raw_resource.category)
        elif len(args.resource) == 2:
            # Is it a Category/Title?
            try:
                category = self.get_resource_category(args.resource[0])
                args.title = args.resource[1]
                return category
            except WaltzResourceNotFound:
                pass
            # Service/Category
            try:
                service = self.get_service(args.resource[0])
                args.service = service.name
                return self.get_resource_category(args.resource[1])
            except WaltzServiceNotFound:
                pass
            except WaltzResourceNotFound:
                pass
            # Service/Title
            service = self.get_service(args.resource[0])
            search_terms['service'] = service.name
            search_terms['title'] = args.resource[1]
            raw_resource = self.find_resource(**search_terms)
            self.fill_args(args, raw_resource)
            return self.get_resource_category(raw_resource.category)
        elif len(args.resource) == 3:
            # Service/Category/Title
            args.service, args.category, args.title = args.resource
            service = self.get_service(args.service)
            args.service = service.name
            return self.get_resource_category(args.resource[1])

    def search(self, category, resource_name, filter_by_services):
        for service_name, service in self.services.items():
            if service_name in filter_by_services or not filter_by_services:
                for result in service.search(category, resource_name):
                    yield result

