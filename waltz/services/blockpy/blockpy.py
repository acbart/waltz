from waltz.exceptions import WaltzException
from waltz.services.blockpy.api import BlockPyAPI
from waltz.services.service import Service


class BlockPy(Service):
    type: str = "blockpy"
    RESOURCES = {}

    CONFIGURATION_SETTINGS = [
        ('email', True, None, 'The email used to login to an instructor/admin account for BlockPy.'),
        ('password', True, None, 'The password for that account.'),
        ('base', True, None, 'The URL base for the BlockPy installation (e.g., "https://think.cs.vt.edu/blockpy/")'),
        ('allow_insecure', False, False, 'Whether to allow insecure HTTPS connections (useful for dev/testing).')
    ]

    def __init__(self, name: str, settings: dict):
        super().__init__(name, settings)
        used_settings = {}
        for field, required, default_value, description in self.CONFIGURATION_SETTINGS:
            if field in settings and settings[field] is not None:
                used_settings[field] = settings[field]
            elif required:
                raise WaltzException("Missing required BlockPy configuration parameter {}".format(field))
            else:
                used_settings[field] = default_value
        self.api = BlockPyAPI(**used_settings)

    @classmethod
    def configure(cls, args):
        return cls(args.new, {
            'base': args.base,
            'email': args.email,
            'password': args.password,
            'allow_insecure': args.allow_insecure
        })

    @classmethod
    def add_parser_configure(cls, parser):
        blockpy_parser = parser.add_parser('blockpy', help="Connect to a BlockPy database")
        blockpy_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        for field, required, default_value, description in cls.CONFIGURATION_SETTINGS:
            blockpy_parser.add_argument('--'+field, help=description)
        return blockpy_parser

    @classmethod
    def add_parser_list(cls, parser, custom_name='blockpy'):
        blockpy_parser = parser.add_parser(custom_name, help="List possible resources on BlockPy")
        blockpy_parser.add_argument('category', type=str, help="The type of resource to list. One of {courses, problems, groups}.")
        blockpy_parser.add_argument('--term', type=str, help="A search term to optionally filter on.", default="")
        blockpy_parser.add_argument('--local_service', type=str, help="Use a different local service than the default.")
        return blockpy_parser

    def list(self, registry, args):
        if args.category in ('course', 'courses', 'blockpy_course', 'blockpy_courses'):
            self.RESOURCES['blockpy_course'].list(registry, self, args)
        elif args.category in ('problem', 'problems', 'blockpy_problem', 'blockpy_problems'):
            self.RESOURCES['problem'].list(registry, self, args)
        elif args.category in ('group', 'groups', 'blockpy_group', 'blockpy_groups'):
            self.RESOURCES['group'].list(registry, self, args)
        # waltz list blockpy courses
        # waltz list blockpy groups
        pass
