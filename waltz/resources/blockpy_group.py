from pprint import pprint

from natsort import natsorted
from tabulate import tabulate

from waltz.resources.resource import Resource
from waltz.tools.utilities import blockpy_string_to_datetime


class BlockPyGroup(Resource):
    name = "blockpy_group"
    name_plural = "blockpy_groups"
    category_names = ["blockpy_group", "blockpy_groups"]

