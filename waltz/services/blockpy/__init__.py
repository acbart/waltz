from waltz.resources.problem import Problem
from waltz.resources.blockpy_course import BlockPyCourse
from waltz.defaults import register_service_type
from waltz.services.blockpy.blockpy import BlockPy


BlockPy.register_resource(Problem)
BlockPy.register_resource(BlockPyCourse)

register_service_type(BlockPy)