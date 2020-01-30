from waltz.exceptions import WaltzException
from waltz.services.canvas.api import CanvasAPI
from waltz.services.service import Service


class Canvas(Service):
    type: str = "canvas"
    RESOURCES = {}
    api: CanvasAPI

    def __init__(self, name: str, settings: dict):
        super().__init__(name, settings)
        token, base, course = settings.get('token'), settings.get('base'), settings.get('course')
        if token and base and course:
            self.api = CanvasAPI(base, token, course)
        else:
            raise WaltzException(("Canvas API needs token, base, and course:\n"
                                  "\ttoken: {}\n\tbase: {}\n\tcourse: {}"
                                  ).format(token, base, course))

    @classmethod
    def configure(cls, args):
        return cls(args.new, {
            'base': args.base,
            'course': args.course,
            'token': args.token,
        })

    @classmethod
    def add_parser_configure(cls, parser):
        canvas_parser = parser.add_parser('canvas', help="Connect to a specific Canvas course")
        canvas_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        canvas_parser.add_argument('--base', type=str, help="The base canvas URL (e.g., https://udel.instructure.com/)")
        canvas_parser.add_argument('--course', type=str, help="The course ID from Canvas (e.g., 17703022)")
        canvas_parser.add_argument('--token', type=str, help="The access token (long string of gibberish)")
        return canvas_parser

    @classmethod
    def add_parser_list(cls, parser, custom_name='canvas'):
        canvas_parser = parser.add_parser(custom_name, help="List possible resources on Canvas")
        canvas_parser.add_argument('category', type=str, help="The type of resource to list.")
        canvas_parser.add_argument('--term', type=str, help="A search term to optionally filter on.", default="")
        canvas_parser.add_argument('--local_service', type=str, help="Use a different local service than the default.")
        return canvas_parser

    def list(self, registry, args):
        self.RESOURCES[args.category].list(registry, self, args)



