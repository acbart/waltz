import json
from pprint import pprint

from natsort import natsorted
from tabulate import tabulate

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.resources.resource import Resource
from waltz.tools.utilities import blockpy_string_to_datetime


class BlockPyCourse(Resource):
    name = "blockpy_course"
    name_plural = "blockpy_courses"
    category_names = ["blockpy_course", "blockpy_courses"]

    @classmethod
    def sort_course(cls, course):
        return course.get('url') or course.get('id')

    @classmethod
    def list(cls, registry, blockpy, args):
        local = registry.get_service(args.local_service, 'local')
        courses = blockpy.api.get('list/courses/')['courses']
        rows = []
        for course in natsorted(courses, key=cls.sort_course):
            created = blockpy_string_to_datetime(course['date_created'])
            rows.append((course['id'], course['url'], course['name'], course['service'], created.strftime('%Y %B')))
        print(tabulate(rows, ('ID', 'Url', 'Name', 'Service', 'Created')))
        #    try:
        #        path = local.find_existing(registry, resource[cls.title_attribute])
        #        rows.append(("Yes", "Yes", resource[cls.title_attribute], os.path.relpath(path)))
        #    except WaltzAmbiguousResource as war:
        #        paths = "\n".join(os.path.relpath(path) for path in war.args[0])
        #        rows.append(("Yes", "Multiple", resource[cls.title_attribute], paths))
        #    except FileNotFoundError:
        #        rows.append(("Yes", "No", resource[cls.title_attribute], ""))
        #print(tabulate(rows, ('Remote', 'Local', 'Title', 'Path')))

    @classmethod
    def download(cls, registry: Registry, args):
        blockpy = registry.get_service(args.service, "blockpy")
        courses = blockpy.api.get('list/courses/')['courses']
        potentials = [course for course in courses if course['url'] == args.title]
        if len(potentials) > 1:
            raise WaltzAmbiguousResource("Too many courses with URL '{}'".format(args.title))
        elif not potentials:
            raise WaltzResourceNotFound("No course with URL '{}' found.".format(args.title))
        bundle = blockpy.api.get('export/', json={'course_id': potentials[0]['id']})
        # Assignments
        for assignment in bundle['assignments']:
            registry.store_resource(blockpy.name, 'problem', assignment['url'], "", json.dumps(assignment))
        # Memberships
        groups_assignments = {}
        for membership in bundle['memberships']:
            if membership['assignment_group_url'] not in groups_assignments:
                groups_assignments[membership['assignment_group_url']] = []
            groups_assignments[membership['assignment_group_url']].append(membership['assignment_url'])
        # Groups
        for group in bundle['groups']:
            group['problems'] = groups_assignments.get(group['url'], [])
            registry.store_resource(blockpy.name, 'blockpy_group', group['url'], "", json.dumps(group))
