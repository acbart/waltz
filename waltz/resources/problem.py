import difflib
import json
import os
import sys
from pprint import pprint

from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    blockpy_string_to_datetime, from_friendly_date, get_parent_directory


# TODO: Template support
# TODO: Sophisticated links
# TODO: File system handling

class Problem(Resource):
    name = "problem"
    name_plural = "problems"
    category_names = ['problem', 'problems', 'coding_problem', 'coding_problems']
    default_service = 'blockpy'
    folder_file = 'index'

    @classmethod
    def find(cls, blockpy, title):
        # TODO: Change blockpy -> registry, title -> args
        bundle = blockpy.api.get('export', json={'assignment_url': title})
        assignments = bundle.get('assignments', [])
        return assignments[0] if assignments else None

    @classmethod
    def upload(cls, registry: Registry, args):
        blockpy = registry.get_service(args.service, cls.default_service)
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=args.category, disambiguate=args.url)
        full_data = json.loads(raw_resource.data)
        blockpy.api.post("import", json={
            'course_id': full_data['course_id'],
            'assignments': [full_data]
        })

    @classmethod
    def decode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        # TODO: use disambiguate
        if args.all:
            raw_resources = registry.find_all_resources(service=args.service, category=cls.name)
        else:
            raw_resources = [registry.find_resource(title=args.title,
                                                    service=args.service, category=cls.name)]
        for raw_resource in raw_resources:
            try:
                destination_path = local.find_existing(registry, raw_resource.title,
                                                       folder_file=cls.folder_file)
            except FileNotFoundError:
                destination_path = local.make_markdown_filename(raw_resource.title,
                                                                folder_file=cls.folder_file)
                if args.destination:
                    destination_path = os.path.join(args.destination, destination_path)
            base = get_parent_directory(destination_path)
            decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
            local.write(destination_path, decoded_markdown)
            for path, data in extra_files:
                local.write(path, data)

    SPECIAL_INSTRUCTOR_FILES = {
        '?': 'hidden but accessible files',
        '!': 'instructor only files',
        '^': 'extra starting files',
        '&': 'read-only files'
    }
    SPECIAL_INSTRUCTOR_FILES_R = {
        value: key for key, value in SPECIAL_INSTRUCTOR_FILES.items()
    }

    @classmethod
    def decode_json(cls, registry: Registry, data: str, args):
        raw_data = json.loads(data)
        result = CommentedMap()
        result['title'] = raw_data['url']
        result['display title'] = raw_data['name']
        result['resource'] = cls.name
        result['type'] = raw_data['type']
        if raw_data['reviewed']:
            result['human reviewed'] = raw_data['reviewed']
        result['visibility'] = CommentedMap()
        result['visibility']['hide status'] = raw_data['hidden']
        result['visibility']['publicly indexed'] = raw_data['public']
        if raw_data['ip_ranges']:
            result['visibility']['ip ranges'] = raw_data['ip_ranges']
        result['additional settings'] = json.loads(raw_data['settings'] or "{}")
        if raw_data['forked_id']:
            result['forked'] = CommentedMap()
            # TODO: Look up forked's url for more info; or perhaps automatically have it downloaded along?
            result['forked']['id'] = raw_data['forked_id']
            result['forked']['version'] = raw_data['forked_version']
        result['identity'] = CommentedMap()
        result['identity']['owner id'] = raw_data['owner_id']
        result['identity']['owner email'] = raw_data['owner_id__email']
        result['identity']['course id'] = raw_data['course_id']
        result['identity']['version downloaded'] = raw_data['version']
        result['identity']['created'] = to_friendly_date_from_datetime(
            blockpy_string_to_datetime(raw_data['date_created']))
        result['identity']['modified'] = to_friendly_date_from_datetime(
            blockpy_string_to_datetime(raw_data['date_modified']))
        # TODO: Tags
        # TODO: Sample Submissions. Have a "samples/" folder?
        # TODO: If args.combine, then put it all into one file
        files_path = raw_data['url']  # "{} files/".format(raw_data['url'])
        result['files'] = CommentedMap()
        result['files']['path'] = files_path
        result['files']['hidden but accessible files'] = []
        result['files']['instructor only files'] = []
        result['files']['extra starting files'] = []
        result['files']['read-only files'] = []
        if hasattr(args, 'destination') and args.destination:
            files_path = os.path.join(args.destination, files_path)
        extra_files = [
            (os.path.join(files_path, "on_run.py"), raw_data['on_run']),
            (os.path.join(files_path, "starting_code.py"), raw_data['starting_code'])
        ]
        if raw_data['on_change']:
            extra_files.append((os.path.join(files_path, "on_change.py"), raw_data['on_change']))
        if raw_data['on_eval']:
            extra_files.append((os.path.join(files_path, "on_eval.py"), raw_data['on_eval']))
        if raw_data['extra_instructor_files']:
            # TODO: Create special manifest file for listing special file types (e.g., "&" and "?")
            extra_instructor_files = json.loads(raw_data['extra_instructor_files'])
            for eif_filename, eif_contents in extra_instructor_files.items():
                if eif_filename[0] in "?!^&*":
                    new_path = os.path.join(files_path, eif_filename[1:])
                    extra_files.append((new_path, eif_contents))
                    special_file_type = cls.SPECIAL_INSTRUCTOR_FILES[eif_filename[0]]
                    result['files'][special_file_type].append(new_path)
        return add_to_front_matter(raw_data['instructions'], result), extra_files

    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title, folder_file=cls.folder_file)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(registry, decoded_markdown, args)
        registry.store_resource(args.service, cls.name, args.title, "", data)

    @classmethod
    def encode_json(cls, registry: Registry, data: str, args):
        regular, waltz, body = extract_front_matter(data)
        # Grab out convenient groups
        visibility = waltz.get('visibility', {})
        forked = waltz.get('forked', {})
        identity = waltz.get('identity', {})
        files = waltz.get('files', {})
        # Grab any extra files
        extra_files = {}
        local = registry.get_service(args.local_service, 'local')
        for py_filename in ['on_run', 'starting_code', 'on_change',
                            'on_eval']:
            try:
                source_path = local.find_existing(registry, args.title,
                                                  folder_file=py_filename,
                                                  extension='.py')
            except FileNotFoundError:
                extra_files[py_filename] = ""
                continue
            extra_files[py_filename] = local.read(source_path)
        collected = {}
        for special, prepend in cls.SPECIAL_INSTRUCTOR_FILES_R.items():
            for file in files.get(special, []):
                source_path = local.find_existing(registry, args.title,
                                                  folder_file=file,
                                                  extension="")
                collected[prepend+file] = local.read(source_path)
        if collected:
            extra_files['extra_instructor_files'] = json.dumps(collected)
        else:
            extra_files['extra_instructor_files'] = ""

        # And generate the rest of the JSON
        return json.dumps({
            "_schema_version": 2,
            'url': waltz['title'],
            'name': waltz['display title'],
            'type': waltz['type'],
            'reviewed': waltz.get('human reviewed', False),
            'hidden': visibility.get('hide status'),
            'public': visibility.get('publicly indexed'),
            'ip_ranges': visibility.get('ip ranges', ""),
            'settings': json.dumps(waltz['additional settings'])
                        if waltz['additional settings'] else None,
            'forked_id': forked.get('id', None),
            'forked_version': forked.get('version', None),
            'owner_id': identity['owner id'],
            'owner_id__email': identity['owner email'],
            'course_id': identity['course id'],
            'version': identity['version downloaded'],
            'date_created': from_friendly_date(identity.get('created')),
            'date_modified': from_friendly_date(identity.get('modified')),
            'instructions': body,
            'extra_starting_files': "",
            # TODO: Store sample submissions in BlockPy
            'sample_submissions': [],
            # TODO: Store tags in BlockPy
            'tags': [],
            **extra_files
            # TODO: Other fields
        })

    @classmethod
    def diff_extra_files(cls, registry: Registry, data, args):
        local = registry.get_service(args.local_service, 'local')
        for py_filename in ['on_run', 'starting_code', 'on_change',
                            'on_eval']:
            try:
                source_path = local.find_existing(registry, args.title,
                                                  folder_file=py_filename,
                                                  extension='.py')
            except FileNotFoundError:
                yield py_filename, ""
                continue
            print(source_path)
            yield source_path, local.read(source_path)
