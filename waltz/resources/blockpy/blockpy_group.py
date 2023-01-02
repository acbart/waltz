import json
from pprint import pprint
import os

from natsort import natsorted
from ruamel.yaml.comments import CommentedMap
from tabulate import tabulate

from waltz.registry import Registry
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import add_to_front_matter, extract_front_matter, hide_data_in_html, m2h
from waltz.tools.utilities import blockpy_string_to_datetime, to_friendly_date_from_datetime
from waltz.resources.blockpy.blockpy_resource import BlockPyResource


class BlockPyGroup(BlockPyResource):
    name = "blockpy_group"
    name_plural = "blockpy_groups"
    category_names = ["blockpy_group", "blockpy_groups"]
    folder_file = 'index'

    @classmethod
    def decode_json(cls, registry: Registry, data: str, args):
        raw_data = json.loads(data)
        result = CommentedMap()
        result['title'] = raw_data['url']
        result['display title'] = raw_data['name']
        result['resource'] = cls.name
        result['position'] = raw_data['position']
        # Identity
        result['identity'] = CommentedMap()
        result['identity']['owner id'] = raw_data['owner_id']
        result['identity']['owner email'] = raw_data['owner_id__email']
        result['identity']['course id'] = raw_data['course_id']
        # TODO: Fixed, need to remove value
        result['identity']['version downloaded'] = raw_data.get('version', None)
        result['identity']['created'] = to_friendly_date_from_datetime(
            blockpy_string_to_datetime(raw_data['date_created']))
        result['identity']['modified'] = to_friendly_date_from_datetime(
            blockpy_string_to_datetime(raw_data['date_modified']))
        # Forked
        if raw_data['forked_id']:
            result['forked'] = CommentedMap()
            # TODO: Look up forked's url for more info; or perhaps automatically have it downloaded along?
            result['forked']['id'] = raw_data['forked_id']
            result['forked']['version'] = raw_data['forked_version']
        problems = "\n".join(map(str, raw_data['problems']))
        # TODO: Finish dumping the problems
        extra_files = []
        return add_to_front_matter(problems, result), extra_files

    @classmethod
    def encode_json(cls, registry: Registry, data, args):
        # TODO: Finish this
        raise NotImplementedError("Oops, not done yet!")
        regular, waltz, body = extract_front_matter(data)
        identity = waltz.get('identity', {})
        problems = []
        groups = {}
        for question in waltz.get('questions', []):
            if isinstance(question, str):
                # Look up quiz question name
                questions.append(QuizQuestion.encode_question_by_title(registry, question, args))
            elif 'group' in question:
                # This is a question group
                group = QuizGroup.encode_group(registry, question, args)
                groups[group['name']] = group
                questions.extend(QuizGroup.encode_questions(registry, question, args))
            else:
                # This is an embedded question
                questions.append(QuizQuestion.encode_question(registry, question, args))
        # TODO: total_estimated_points from the questions
        return json.dumps({
            'title': waltz['title'],
            'published': waltz.get('published', False),
            'description': body,
            # Settings
            'quiz_type': settings.get('quiz_type', 'assignment'),
            'points_possible': settings.get('points_possible'),
            'allowed_attempts': settings.get('allowed_attempts'),
            'scoring_policy': settings.get('scoring_policy'),
            # Timing
            'due_at': from_friendly_date(timing.get('due_at')),
            'unlock_at': from_friendly_date(timing.get('unlock_at')),
            'lock_at': from_friendly_date(timing.get('lock_at')),
            # Secrecy
            'one_question_at_a_time': secrecy.get('one_question_at_a_time'),
            'shuffle_answers': secrecy.get('shuffle_answers'),
            'time_limit': secrecy.get('time_limit'),
            'cant_go_back': secrecy.get('cant_go_back'),
            'show_correct_answers': secrecy.get('show_correct_answers'),
            'show_correct_answers_last_attempt': secrecy.get('show_correct_answers_last_attempt'),
            'show_correct_answers_at': secrecy.get('show_correct_answers_at'),
            'hide_correct_answers_at': secrecy.get('hide_correct_answers_at'),
            'hide_results': secrecy.get('hide_results'),
            'one_time_results': secrecy.get('one_time_results'),
            'access_code': secrecy.get('access_code'),
            'ip_filter': secrecy.get('ip_filter'),
            # Questions and Groups
            'questions': questions,
            'groups': groups
        })