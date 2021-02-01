import difflib
import io
import json
import os
import sys
import zipfile
from pprint import pprint

from natsort import natsorted
from ruamel.yaml.comments import CommentedMap
from tabulate import tabulate

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    blockpy_string_to_datetime, from_friendly_date, find_all_files


# TODO: Template support
# TODO: Sophisticated links
# TODO: File system handling

class GradeScopeAssignment(Resource):
    name = "gradescope_assignment"
    name_plural = "gradescope_assignments"
    category_names = ['gradescope_assignment', 'gradescope_assignments']
    default_service = 'gradescope'
    folder_file = 'index'

    @classmethod
    def sort_assignment(cls, assignment):
        return assignment.name,

    @classmethod
    def list(cls, registry, gradescope, args):
        local = registry.get_service(args.local_service, 'local')
        rows = []
        gradescope.api.get_account()
        instructor_courses = gradescope.api.account.instructor_courses
        course = instructor_courses[str(gradescope.api.course)]
        course._lazy_load_assignments()
        assignments = course.assignments.values()
        for assignment in natsorted(assignments, key=cls.sort_assignment):
            rows.append((assignment.aid, assignment.name, assignment.points, len(assignment.questions)))
        print(tabulate(rows, ('AID', 'Name', 'Points', 'Questions')))

    @classmethod
    def find(cls, gradescope, title):
        # TODO: Change blockpy -> registry, title -> args
        gradescope.api.get_account()
        instructor_courses = gradescope.api.account.instructor_courses
        course = instructor_courses[str(gradescope.api.course)]
        course._lazy_load_assignments()
        for assignment in course.assignments.values():
            if assignment.name == title:
                return assignment


    @classmethod
    def upload(cls, registry: Registry, args):
        gradescope = registry.get_service(args.service, cls.default_service)
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=cls.name, disambiguate="")
        full_assignment = raw_resource.data
        remote_assignment = cls.find(gradescope, args.title)
        if remote_assignment is None:
            raise WaltzResourceNotFound(f"No GradeScope assignment with title '{args.title}' found.")

        remote_assignment.configure(full_assignment)


    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title, folder_file=cls.folder_file)
        decoded_markdown = local.read(source_path)
        data = cls.encode_extra(registry, decoded_markdown, args)
        registry.store_resource(args.service, cls.name, args.title, "", data)

    @classmethod
    def encode_extra(cls, registry: Registry, data: str, args):
        local = registry.get_service(args.local_service, 'local')
        regular, waltz, body = extract_front_matter(data)
        # Grab any extra files
        files = waltz.get('files', [])
        for path in ['setup.sh', 'run_autograder']:
            if path not in files:
                files.append(path)
        local = registry.get_service(args.local_service, 'local')

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for filename in files:
                try:
                    # TODO: Allow to match wildcards!!
                    source_path = local.find_existing(registry, args.title,
                                                      folder_file=filename,
                                                      extension="")
                except FileNotFoundError:
                    continue
                if os.path.isdir(source_path):
                    print("Adding all from", source_path, "as", filename)
                    for inner_file in find_all_files(source_path):
                        print(os.path.join(source_path, inner_file), os.path.join(filename, inner_file))
                        zip_file.write(os.path.join(source_path, inner_file), os.path.join(filename, inner_file))
                else:
                    print("Adding", source_path, "as", filename)
                    zip_file.write(source_path, filename)

        # And generate the rest of the JSON
        return zip_buffer.getvalue()
