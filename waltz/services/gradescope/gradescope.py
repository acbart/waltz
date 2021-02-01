from waltz.exceptions import WaltzException
from waltz.services.gradescope.pyscope.pyscope import GSConnection, ConnState
from waltz.services.service import Service


class GradeScope(Service):
    type: str = "gradescope"
    RESOURCES = {}

    CONFIGURATION_SETTINGS = [
        ('email', True, None, 'The email used to login to an account for GradeScope.'),
        ('password', True, None, 'The password for that account.'),
        ('course', True, None, 'The course to access assignments from.')
    ]

    def __init__(self, name: str, settings: dict):
        super().__init__(name, settings)
        used_settings = {}
        for field, required, default_value, description in self.CONFIGURATION_SETTINGS:
            if field in settings and settings[field] is not None:
                used_settings[field] = settings[field]
            elif required:
                raise WaltzException("Missing required GradeScope configuration parameter {}".format(field))
            else:
                used_settings[field] = default_value
        self.api = GSConnection(used_settings['course'])
        success = self.api.login(used_settings['email'], used_settings['password'])
        # WARNING
        if not success or self.api.state != ConnState.LOGGED_IN:
            print("Warning: Not currently logged in to GradeScope")

    @classmethod
    def configure(cls, args):
        return cls(args.new, {
            'email': args.email,
            'password': args.password,
            'course': args.course
        })

    @classmethod
    def add_parser_configure(cls, parser):
        gradescope_parser = parser.add_parser('gradescope', help="Connect to GradeScope")
        gradescope_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        for field, required, default_value, description in cls.CONFIGURATION_SETTINGS:
            gradescope_parser.add_argument('--'+field, help=description)
        return gradescope_parser

    @classmethod
    def add_parser_list(cls, parser, custom_name='gradescope'):
        gradescope_parser = parser.add_parser(custom_name, help="List possible resources on GradeScope")
        gradescope_parser.add_argument('category', type=str, help="The type of resource to list. One of {courses, assignments}.")
        gradescope_parser.add_argument('--term', type=str, help="A search term to optionally filter on.", default="")
        gradescope_parser.add_argument('--local_service', type=str, help="Use a different local service than the default.")
        return gradescope_parser

    def list(self, registry, args):
        if args.category in ('course', 'courses', 'gradescope_course', 'gradescope_courses'):
            self.RESOURCES['gradescope_course'].list(registry, self, args)
        elif args.category in ('gradescope_assignment', 'gradescope_assignments'):
            self.RESOURCES['gradescope_assignment'].list(registry, self, args)
