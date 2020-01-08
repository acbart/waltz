from waltz.defaults import register_service_type
from waltz.resources.assignment import Assignment
from waltz.resources.quiz import Quiz
from waltz.services.canvas.canvas import Canvas
from waltz.resources.page import Page
from waltz.services.canvas.api import CanvasAPI

Canvas.register_resource(Page)
Canvas.register_resource(Quiz)
Canvas.register_resource(Assignment)

register_service_type(Canvas)