from waltz.defaults import register_default_service
from waltz.services.service import Service


class Canvas(Service):
    def copy(self, updates):
        settings = {}
        if updates.base:
            settings['base'] = updates.base
        if updates.token:
            settings['token'] = updates.token
        if updates.course:
            settings['course'] = updates.course
        return Canvas(updates.new, 'canvas', settings, False)

    def add_parser_copy(self, parser):
        canvas_parser = parser.add_parser('canvas', help="Connect to a specific Canvas course")
        canvas_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        canvas_parser.add_argument('--base', type=str, help="The base canvas URL (e.g., https://udel.instructure.com/)")
        canvas_parser.add_argument('--token', type=str, help="The access token (long string of gibberish)")
        canvas_parser.add_argument('--course', type=str, help="The course ID from Canvas (e.g., 17703022)")
        return canvas_parser


CANVAS = Canvas('canvas', None, {}, True)

register_default_service(CANVAS)