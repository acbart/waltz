from waltz import defaults
from waltz.services.service import Service


class Local(Service):
    """
    The local filesystem, which can hold a lot of resources in different styles.
    """
    name: str
    parent_name : str

    @classmethod
    def in_new_position(cls, path):
        return Local('local', 'local', {'path': path}, False)

    def copy(self, updates):
        return Local(updates.name, 'local', {'path': updates.path}, False)

    def add_parser_copy(self, parser):
        local_parser = parser.add_parser('local', help="Create another local filesystem to connect to.")
        local_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        local_parser.add_argument('path', type=str, help="The path to the directory")
        return local_parser


LOCAL = Local('local', None, {'path': None}, True)

defaults.register_default_service(LOCAL)