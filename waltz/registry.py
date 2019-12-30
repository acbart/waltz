import logging
import os

from waltz import defaults as defaults
from waltz.exceptions import WaltzException
from waltz.services.service import services_from_data, services_as_data
from waltz.course import Course, courses_as_data, courses_from_data
from waltz.yaml_setup import yaml


class Registry:
    """
    A collection of available courses and default services.
    """
    courses: 'Dict[str, Course]'
    services: 'Dict[str, Service]'
    default_course: str
    filename: str
    version: str

    def __init__(self, filename, courses, services, default_course, version):
        self.filename = filename
        self.courses = courses
        self.services = services
        self.default_course = default_course
        self.version = version

    @classmethod
    def load_version_010(cls, filename, data):
        default_services = defaults.get_default_services()
        global_services = services_from_data(data['services'], default_services)
        default_services.update(global_services)
        return Registry(filename=filename,
                        courses=courses_from_data(data['courses'], default_services),
                        services=global_services,
                        default_course=data['default_course'],
                        version=data['version'])

    @classmethod
    def from_file(cls, filename):
        if os.path.exists(filename):
            with open(filename) as registry_file:
                registry_data = yaml.load(registry_file)
            version = registry_data['version']
            if version in ('0.1.0', ):
                return Registry.load_version_010(filename, registry_data)
            else:
                raise WaltzException("Unknown registry file version: {}\nMy version is: {}".format(
                    version, defaults.WALTZ_VERSION))
        else:
            if filename == defaults.REGISTRY_PATH:
                logging.warning("No registry file was detected; since default was specified, I'll create it instead.")
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                return cls.make_default(filename).save_to_file()
            else:
                raise WaltzException("Registry file specified was not found: {}".format(filename))

    @classmethod
    def make_default(cls, filename) -> 'Registry':
        return Registry(filename, courses={}, services=defaults.get_default_services(),
                        default_course=None, version=defaults.WALTZ_VERSION)

    def save_to_file(self):
        with open(self.filename, 'w') as registry_file:
            yaml.dump({
                'version': self.version,
                'courses': courses_as_data(self.courses),
                'services': services_as_data(self.services),
                'default_course': self.default_course
            }, registry_file)
        return self

    def add_course(self, name, local_service):
        self.courses[name] = Course(name, {'local': local_service})

    def copy_service(self, old, args, globally):
        new_service = self.services[old].copy(args)
        if globally:
            self.services[new_service.name] = new_service
        else:
            self.courses[self.default_course].services[new_service.name] = new_service
