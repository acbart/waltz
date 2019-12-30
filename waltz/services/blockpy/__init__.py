from waltz.defaults import register_default_service
from waltz.services.service import Service


class BlockPy(Service):
    def copy(self, updates):
        pass

    def add_parser_copy(self, parser):
        blockpy_parser = parser.add_parser('blockpy', help="Connect to a BlockPy database")
        blockpy_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        blockpy_parser.add_argument('--base', type=str, help="The base server URL (e.g., https://think.cs.vt.edu/blockpy/)")
        blockpy_parser.add_argument('--username', type=str, help="The username to access data with")
        blockpy_parser.add_argument('--password', type=str, help="The password to access data with")
        return blockpy_parser


BLOCKPY = BlockPy('blockpy', None, {}, True)
register_default_service(BLOCKPY)