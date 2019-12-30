from waltz.services.service import services_as_data, services_from_data


class Course:
    """
    Technically speaking, the Course itself is intangible. You are given access to its various
    Resources (in different Styles) via the Services associated with the Course. By default,
    a Course would be expected to have at least the Local Service, which is a directory.
    """
    name: str
    services: 'Dict[str, Service]'

    def __init__(self, name: str, services: 'Dict[str, Service]'):
        self.name = name
        self.services = services

    def as_data(self):
        return {
            'name': self.name,
            'services': services_as_data(self.services)
        }

    @classmethod
    def from_data(cls, data, existing_services):
        return Course(data['name'], services_from_data(data['services'], existing_services))


def courses_as_data(courses):
    return {name: course.as_data() for name, course in courses.items()}


def courses_from_data(courses, existing_services):
    return {name: Course.from_data(course, existing_services) for name, course in courses.items()}