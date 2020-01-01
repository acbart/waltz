from waltz.defaults import register_default_service
from waltz.services.canvas.canvas import Canvas
from waltz.services.canvas.page import Page
from waltz.services.canvas.api import CanvasAPI

Canvas.register_resource(Page)

CANVAS = Canvas('canvas', None, {}, True)

register_default_service(CANVAS)