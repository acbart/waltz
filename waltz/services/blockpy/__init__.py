from waltz.resources.blockpy.blockpy_group import BlockPyGroup
from waltz.resources.blockpy.problem import Problem
from waltz.resources.blockpy.blockpy_course import BlockPyCourse
from waltz.defaults import register_service_type
from waltz.services.blockpy.blockpy import BlockPy


BlockPy.register_resource(Problem)
BlockPy.register_resource(BlockPyCourse)
BlockPy.register_resource(BlockPyGroup)

register_service_type(BlockPy)