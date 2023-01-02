import difflib
import json
import os
import sys
from pprint import pprint

from ruamel.yaml.comments import CommentedMap

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    blockpy_string_to_datetime, from_friendly_date
from waltz.resources.blockpy.blockpy_resource import BlockPyResource


# TODO: Template support
# TODO: Sophisticated links
# TODO: File system handling

class Problem(BlockPyResource):
    name = "problem"
    name_plural = "problems"
    category_names = ['problem', 'problems', 'coding_problem', 'coding_problems']
    folder_file = 'index'

    @classmethod
    def find(cls, blockpy, title):
        # TODO: Change blockpy -> registry, title -> args
        bundle = blockpy.api.get('export', json={'assignment_url': title})
        assignments = bundle.get('assignments', [])
        return assignments[0] if assignments else None

    @classmethod
    def verify_bundle(cls, bundle):
        if 'success' in bundle:
            if bundle['success']:
                return True
            if 'message' in bundle:
                raise Exception(f"Invalid BlockPy Bundle: {bundle['message']}\n{bundle!r}")
            else:
                raise Exception(f"Invalid BlockPy Bundle: (no message)\n{bundle!r}")

    @classmethod
    def download(cls, registry: Registry, args):
        blockpy = registry.get_service(args.service, "blockpy")
        bundle = blockpy.api.get('export/', json={'assignment_url': args.title})
        cls.verify_bundle(bundle)
        potentials = bundle['assignments']
        # Assignments
        if len(potentials) > 1:
            raise WaltzAmbiguousResource(f"Too many problems with URL '{args.title}'")
        elif not potentials:
            raise WaltzResourceNotFound(f"No problem with URL '{args.title}' found.")
        assignment = potentials[0]
        registry.store_resource(blockpy.name, 'problem', assignment['url'], "", json.dumps(assignment))

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
        if raw_data.get('reviewed'):
            result['human reviewed'] = raw_data['reviewed']
        result['visibility'] = CommentedMap()
        result['visibility']['hide status'] = raw_data['hidden']
        if not raw_data.get('reviewed') and 'human reviewed' in raw_data:
            result['visibility']['human reviewed'] = raw_data['human reviewed']
        result['visibility']['subordinate'] = raw_data.get('subordinate', False)
        result['visibility']['publicly indexed'] = raw_data['public']
        if raw_data.get('ip_ranges'):
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
        files_path = raw_data['url']
        result['files'] = CommentedMap()
        result['files']['path'] = files_path
        result['files']['hidden but accessible files'] = []
        result['files']['instructor only files'] = []
        result['files']['extra starting files'] = []
        result['files']['read-only files'] = []
        # Check if index file exists; if so, that's our directory target
        local = registry.get_service(args.local_service, 'local')
        if args.combine:
            body, extra_files = cls.decode_extra_files_by_type(result, raw_data)
        else:
            body = raw_data['instructions']
            try:
                index_path = local.find_existing(registry, files_path,
                                                 folder_file=cls.folder_file)
                files_path = os.path.dirname(index_path)
                #print(">>>", files_path)
            except FileNotFoundError:
                pass
            #if hasattr(args, 'destination') and args.destination:
            #    files_path = os.path.join(args.destination, files_path)
            # Then build up the extra instructor files
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
        # Put instructions up front and return the result
        return add_to_front_matter(body, result), extra_files

    BLOCKPY_QUIZ_FEEDBACK_KEYWORDS = ['correct', 'wrong', 'feedback', 'wrong_any', 'correct_exact', 'correct_regex']

    @classmethod
    def decode_extra_files_by_type(cls, result, raw_data):
        body = raw_data['instructions']
        if raw_data['type'] == 'reading':
            return body, []
        elif raw_data['type'] == 'quiz':
            try:
                quiz_content = json.loads(body)
            except Exception as error:
                print("JSON Decoding Error in Instructions of:", raw_data['url'])
                return body, []
            try:
                quiz_answers = json.loads(raw_data['on_run']).get('questions', {})
            except Exception as error:
                print("JSON Decoding Error in Quiz Feedback of:", raw_data['url'])
                return body, []
            for question_id, question in quiz_content.get('questions', {}).items():
                quiz_answer = quiz_answers.get(question_id, {})
                for potential in cls.BLOCKPY_QUIZ_FEEDBACK_KEYWORDS:
                    if potential in quiz_answer:
                        question[potential] = quiz_answer[potential]
            body = json.dumps(quiz_content, indent=2)
            return body, []
        elif raw_data['type'] == 'blockpy':
            return body, []

    @classmethod
    def encode_extra_files_by_type(cls, waltz, body):
        extra_files = {
            'on_run': "", 'starting_code': "", 'on_change': "", 'on_eval': ""
        }
        if waltz['type'] == 'reading':
            pass
        elif waltz['type'] == 'quiz':
            try:
                combined_quiz_content = json.loads(body)
            except Exception as error:
                print("JSON Decoding Error in Instructions of:", waltz['title'])
                raise error
            answers = {'questions': {}}
            for question_id, question in combined_quiz_content.get('questions', {}).items():
                answer = answers['questions'][question_id] = {}
                for potential in cls.BLOCKPY_QUIZ_FEEDBACK_KEYWORDS:
                    if potential in question:
                        answer[potential] = question.pop(potential)
            body = json.dumps(combined_quiz_content, indent=2)
            extra_files['on_run'] = json.dumps(answers)
        elif waltz['type'] == 'blockpy':
            pass
        return body, extra_files

    @classmethod
    def encode_json(cls, registry: Registry, data: str, args):
        regular, waltz, body = extract_front_matter(data)
        # Grab out convenient groups
        visibility = waltz.get('visibility', {})
        forked = waltz.get('forked', {})
        identity = waltz.get('identity', {})
        files = waltz.get('files', {})
        # Grab any extra files
        if args.combine:
            body, extra_files = cls.encode_extra_files_by_type(waltz, body)
        else:
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
            'subordinate': waltz.get('subordinate', False) or False,
            'reviewed': waltz.get('human reviewed', False) or False,
            'hidden': visibility.get('hide status', False) or False,
            'public': visibility.get('publicly indexed', False) or False,
            'ip_ranges': visibility.get('ip ranges', ""),
            'settings': json.dumps(waltz['additional settings'])
                        if waltz.get('additional settings') else None,
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
