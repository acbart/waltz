import json
from io import StringIO
from pprint import pprint
from tqdm import tqdm
import os

from types import SimpleNamespace
from natsort import natsorted
from tabulate import tabulate

from ruamel.yaml.comments import CommentedMap

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.resources.blockpy.blockpy_group import BlockPyGroup
from waltz.resources.blockpy.problem import Problem
from waltz.resources.blockpy.blockpy_resource import BlockPyResource
from waltz.tools.utilities import blockpy_string_to_datetime, replace_namespace
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter, extract_front_matter
from waltz.tools.yaml_setup import yaml


class BlockPyCourse(BlockPyResource):
    name = "blockpy_course"
    name_plural = "blockpy_courses"
    category_names = ["blockpy_course", "blockpy_courses"]

    @classmethod
    def sort_course(cls, course):
        return course.get('url') or course.get('id')

    @classmethod
    def find(cls, blockpy, title):
        # TODO: Change blockpy -> registry, title -> args
        try:
            course, groups, problems = cls.get_full_course(blockpy, title)
        except WaltzResourceNotFound:
            return None
        return course

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
        course, groups, problems = cls.get_full_course(blockpy, args.title)
        for url, contents in problems.items():
            registry.store_resource(blockpy.name, 'problem', url, "", json.dumps(contents))
        for url, contents in groups.items():
            registry.store_resource(blockpy.name, "blockpy_group", url, "", json.dumps(contents))
        registry.store_resource(blockpy.name, "blockpy_course", args.title, course['id'], json.dumps(course))

    @classmethod
    def get_full_course(cls, blockpy, title):
        courses = blockpy.api.get('list/courses/')['courses']
        potentials = [course for course in courses if course['url'] == title]
        if len(potentials) > 1:
            raise WaltzAmbiguousResource("Too many courses with URL '{}'".format(title))
        elif not potentials:
            raise WaltzResourceNotFound("No course with URL '{}' found.".format(title))
        course_id = potentials[0]['id']
        bundle = blockpy.api.get('export/', json={'course_id': course_id})
        records = {
            'problems': {},
            'groups': [],
            **potentials[0]
        }
        course, groups, problems = {}, {}, {}
        # Memberships
        groups_assignments = {}
        for membership in bundle['memberships']:
            if membership['assignment_group_url'] not in groups_assignments:
                groups_assignments[membership['assignment_group_url']] = []
                records['problems'][membership['assignment_group_url']] = []
            better_url = membership['assignment_url']
            if better_url is None:
                better_url = membership['assignment_id']
            groups_assignments[membership['assignment_group_url']].append(better_url)
            records['problems'][membership['assignment_group_url']].append(better_url)
        # Assignments
        for assignment in bundle['assignments']:
            problems[assignment['url']] = assignment
        # Groups
        for group in bundle['groups']:
            group['problems'] = groups_assignments.get(group['url'], [])
            records['groups'].append(group['url'])
        return records, groups, problems


    @classmethod
    def decode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        raw_resource = registry.find_resource(title=args.title, service=args.service, category=cls.name)
        destination_path = local.find_or_new(registry, raw_resource, None, args)
        decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
        local.write(destination_path, decoded_markdown)

        if args.all:
            data = json.loads(raw_resource.data)
            for group in tqdm(data['groups']):
                custom_args = replace_namespace(args, title=group)
                BlockPyGroup.decode(registry, custom_args)
            for group, problems in tqdm(data['problems'].items(), desc='Group'):
                print(group)
                for problem in tqdm(problems, desc='Problem'):
                    print(problem)
                    custom_args = replace_namespace(args, title=problem, destination=group, all=False)
                    Problem.decode(registry, custom_args)

    @classmethod
    def decode_json(cls, registry: Registry, data, args):
        data = json.loads(data)
        result = CommentedMap()
        extra_files = []
        main_files = {}
        for group in tqdm(data['groups']):
            print(group)
            raw_group = registry.find_resource(title=group, service=args.service, category="blockpy_group")
            custom_args = replace_namespace(args, title=group)
            main_group_file, extra_group_files = BlockPyGroup.decode_json(registry, raw_group.data, custom_args)
            main_files[group] = []
            extra_files.append((group, main_group_file))
            extra_files.extend([(group+"/"+filename, contents) for filename, contents in extra_group_files])
        for group, problems in tqdm(data['problems'].items(), desc='Group'):
            for problem in tqdm(problems, desc='Problem'):
                raw_problem = registry.find_resource(title=problem, service=args.service, category="problem")
                custom_args = replace_namespace(args, title=problem, destination=group, all=False)
                main_problem_file, extra_problem_files = Problem.decode_json(registry, raw_problem.data, custom_args)
                main_files[group].append(problem)
                extra_files.append((group+"/"+problem, main_problem_file))
                extra_files.extend([(group+"/"+problem+"/"+filename, contents) for filename, contents in extra_problem_files])
        body = "\n".join(f"{group}:"+(
                         ("\n" + "\n".join([f"   - {problem}" for problem in problems])) if problems else " []"
                         ) for group, problems in main_files.items())
        return add_to_front_matter(body, result), extra_files

    @classmethod
    def diff_extra_files(cls, registry: Registry, data, args):
        local = registry.get_service(args.local_service, 'local')
        regular, waltz, body = extract_front_matter(data)
        course_body = yaml.load(StringIO(body))
        folder_file = None if args.combine else 'index'
        for group, problems in tqdm(course_body.items()):
            try:
                destination_path = local.find_existing(registry, group, folder_file=folder_file, check_front_matter=True)
                yield group, local.read(destination_path)
            except FileNotFoundError:
                pass
            for problem in tqdm(problems, desc="Problem"):
                try:
                    destination_path = local.find_existing(registry, problem, folder_file=folder_file, check_front_matter=True)
                    yield group+"/"+problem, local.read(destination_path)
                except FileNotFoundError:
                    pass
