from waltz.defaults import register_service_type
from waltz.services.service import Service


class BlockPy(Service):
    type: str = "blockpy"
    RESOURCES = {}

    @classmethod
    def configure(cls, args):
        pass

    @classmethod
    def add_parser_configure(cls, parser):
        blockpy_parser = parser.add_parser('blockpy', help="Connect to a BlockPy database")
        blockpy_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        blockpy_parser.add_argument('--base', type=str, help="The base server URL (e.g., https://think.cs.vt.edu/blockpy/)")
        blockpy_parser.add_argument('--username', type=str, help="The username to access data with")
        blockpy_parser.add_argument('--password', type=str, help="The password to access data with")
        return blockpy_parser

    @classmethod
    def add_parser_list(cls, parser):
        return parser


register_service_type(BlockPy)