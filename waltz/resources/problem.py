import difflib
import json
import os
import sys

from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    blockpy_string_to_datetime


# TODO: Template support
# TODO: Sophisticated links
# TODO: File system handling

class Problem(Resource):
    name = "problem"
    name_plural = "problems"
    category_names = ['problem', 'problems', 'coding_problem', 'coding_problems']

    @classmethod
    def upload(cls, registry: Registry, args):
        # TODO: fix
        canvas = registry.get_service(args.service, "canvas")
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=args.category, disambiguate=args.url)
        full_page = json.loads(raw_resource.data)
        canvas.api.put("pages/{url}".format(url=full_page['title']), data={
            'wiki_page[title]': full_page['title'],
            'wiki_page[body]': full_page['body'],
            'wiki_page[published]': full_page['published']
        })
        # TODO: Handle other fields
        # wiki_page[editing_roles]
        # wiki_page[notify_of_update]
        # wiki_page[front_page]

    @classmethod
    def decode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        # TODO: use disambiguate
        if args.all:
            raw_resources = registry.find_all_resources(service=args.service, category=cls.name)
        else:
            raw_resources = [registry.find_resource(title=args.title, service=args.service, category=cls.name)]
        for raw_resource in raw_resources:
            try:
                destination_path = local.find_existing(registry, raw_resource.title)
            except FileNotFoundError:
                destination_path = local.make_markdown_filename(raw_resource.title)
                if args.destination:
                    destination_path = os.path.join(args.destination, destination_path)
            decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
            local.write(destination_path, decoded_markdown)
            for path, data in extra_files:
                local.write(path, data)

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
        result['identity']['created'] = to_friendly_date_from_datetime(blockpy_string_to_datetime(raw_data['date_created']))
        result['identity']['modified'] = to_friendly_date_from_datetime(
            blockpy_string_to_datetime(raw_data['date_modified']))
        # TODO: Tags
        # TODO: Sample Submissions. Have a "sample submissions/" folder?
        # TODO: Decode any waltz data in the extra instructor file "!waltz_data.blockpy"
        # TODO: If args.combine, then put it all into one file
        # TODO: args.instructor_files could be "{name} files/", "./", or something custom?
        # TODO: args.sample_files could be "{name} samples/", "./", "{name} files/samples/" or something custom?
        files_path = "{} files/".format(raw_data['url'])
        result['files'] = CommentedMap()
        result['files']['path'] = files_path
        result['files']['hidden but accessible files'] = []
        result['files']['instructor only files'] = []
        result['files']['extra starting files'] = []
        result['files']['read-only files'] = []
        if args.destination:
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
                    extra_files.append((os.path.join(files_path, eif_filename[1:]), eif_contents))
        return add_to_front_matter(raw_data['instructions'], result), extra_files

    @classmethod
    def encode_json(cls, registry: Registry, data: str, args):
        # TODO: Fix
        regular, waltz, body = extract_front_matter(data)
        body = hide_data_in_html(regular, m2h(body))
        return json.dumps({
            'title': waltz['title'],
            'published': waltz['published'],
            'body': body
            # TODO: Other fields
        })
