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
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    to_friendly_date, from_friendly_date


class Assignment(CanvasResource):
    name = "assignment"
    name_plural = "assignments"
    category_names = ['assignment', 'assignments']
    id = "id"
    endpoint = "assignments/"
    title_attribute = 'name'

    @classmethod
    def decode_json(cls, registry: Registry, data: str, args):
        raw_data = json.loads(data)
        result = CommentedMap()
        result['title'] = raw_data['name']
        result['resource'] = 'assignment'
        result['url'] = raw_data['html_url']
        result['published'] = raw_data['published']
        # General settings
        result['settings'] = CommentedMap()
        result['settings']['points_possible'] = raw_data['points_possible']
        result['settings']['grading_type'] = raw_data['grading_type']
        # Submissions
        result['settings']['submission'] = CommentedMap()
        if 'allowed_extensions' in raw_data:
            result['settings']['submission']['allowed_extensions'] = raw_data['allowed_extensions']
        result['settings']['submission']['submission_types'] = raw_data['submission_types']
        if 'external_tool' in raw_data['submission_types']:
            result['settings']['submission']['external_tool'] = raw_data['external_tool_tag_attributes']['url']
        # Timing
        result['settings']['timing'] = CommentedMap()
        result['settings']['timing']['due_at'] = to_friendly_date(raw_data['due_at'])
        result['settings']['timing']['unlock_at'] = to_friendly_date(raw_data['unlock_at'])
        result['settings']['timing']['lock_at'] = to_friendly_date(raw_data['lock_at'])
        # Secrecy
        result['settings']['secrecy'] = CommentedMap()
        result['settings']['secrecy']['anonymize_students'] = raw_data['anonymize_students']
        result['settings']['secrecy']['anonymous_grading'] = raw_data['anonymous_grading']
        return h2m(raw_data['description'], result), []

    @classmethod
    def upload(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        raw_resource = registry.find_resource(title=args.title, service=canvas.name,
                                              category=cls.name, disambiguate="")
        full_assignment = json.loads(raw_resource.data)
        assignment_data = cls._make_canvas_upload(registry, full_assignment, args)
        remote_assignment = cls.find(canvas, args.title)
        if remote_assignment is None:
            canvas.api.post('assignments/', data=assignment_data)
        else:
            canvas.api.put("assignments/{aid}".format(aid=remote_assignment['id']), data=assignment_data)

    @classmethod
    def _make_canvas_upload(cls, registry: Registry, data, args):
        return {
            'assignment[notify_of_update]': 'false',
            'assignment[name]': data['name'],
            'assignment[description]': data['description'],
            # 'assignment[submission_types][]': ','.join(self.submission_types),
            # 'assignment[allowed_extensions][]': ','.join(self.submission_types),
            'assignment[points_possible]': data['points_possible'],
            'assignment[lock_at]': data['lock_at'],
            'assignment[unlock_at]': data['unlock_at'],
            'assignment[due_at]': data['due_at'],
            'assignment[published]': json.dumps(data.get('published', False)),
        }

    @classmethod
    def encode_json(cls, registry: Registry, data: str, args):
        regular, waltz, body = extract_front_matter(data)
        settings = waltz.get('settings', {})
        submission = settings.get('submission', {})
        timing = settings.get('timing', {})
        secrecy = settings.get('secrecy', {})
        body = hide_data_in_html(regular, m2h(body))
        return json.dumps({
            'name': waltz['title'],
            'description': body,
            'html_url': waltz.get('url', ''),
            'published': waltz['published'],
            # General settings
            'points_possible': settings['points_possible'],
            'grading_type': settings.get('grading_type'),
            # Submissions
            'allowed_extensions': submission.get('allowed_extensions'),
            'submission_types': submission['submission_types'],
            # Timing
            'due_at': from_friendly_date(timing['due_at']),
            'unlock_at': from_friendly_date(timing['unlock_at']),
            'lock_at': from_friendly_date(timing['lock_at']),
            # Secrecy
            'anonymize_students': secrecy.get('anonymize_students', False),
            'anonymous_grading': secrecy.get('anonymous_grading', False)
        })
