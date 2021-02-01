import json
from pprint import pprint
from tqdm import tqdm
import os

from types import SimpleNamespace
from natsort import natsorted
from tabulate import tabulate

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.resources.resource import Resource
from waltz.tools.utilities import blockpy_string_to_datetime


class GradeScopeCourse(Resource):
    name = "gradescope_course"
    name_plural = "gradescope_courses"
    category_names = ["gradescope_course", "gradescope_courses"]

    # TODO: Fill in rest

    @classmethod
    def sort_course(cls, course):
        return (tuple(reversed(course.year.split(" "))), course.shortname)

    @classmethod
    def list(cls, registry, gradescope, args):
        local = registry.get_service(args.local_service, 'local')
        rows = []
        print(gradescope.api.account)
        gradescope.api.get_account()
        student_courses = gradescope.api.account.student_courses
        for course in natsorted(student_courses.values(), key=cls.sort_course):
            rows.append(('Student', course.cid, course.shortname, course.name, course.year, len(course.assignments),
                         len(course.roster)))
        instructor_courses = gradescope.api.account.instructor_courses
        for course in natsorted(instructor_courses.values(), key=cls.sort_course):
            rows.append(('Instructor', course.cid, course.shortname, course.name, course.year, len(course.assignments), len(course.roster)))
        print(tabulate(rows, ('Role', 'CID', 'Shortname', 'Name', 'Year', 'Assignments', 'Roster')))

