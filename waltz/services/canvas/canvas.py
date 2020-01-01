import logging

from waltz.services.canvas.api import CanvasAPI
from waltz.services.canvas.page import Page
from waltz.services.service import Service


class Canvas(Service):
    RESOURCES = {}
    api: CanvasAPI

    def __init__(self, name: str, parent: str, settings: dict, default=False):
        super().__init__(name, parent, settings, default)
        token, base, course = settings.get('token'), settings.get('base'), settings.get('course')
        if token and base and course:
            self.api = CanvasAPI(base, token, course)
        else:
            self.api = None

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

    def search(self, category, resource):
        if not self.api:
            logging.warning("Cannot use service {}, API is not ready.".format(self.name))
            return []

        if category in ('pages', 'page'):
            course = self.api.get("/")
            print(course)
            pages = self.api.get("pages/", data={"search_term": resource}, retrieve_all=True)
            print(pages)
            f
            #return [Page(self.api.get("pages", page.url).to_json()) for page in pages]