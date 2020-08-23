import json
import os
from pprint import pprint
from typing import Type

from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter, m2h
from waltz.tools.html_markdown_utilities import hide_data_in_html
from waltz.tools.utilities import make_safe_filename


class QuizQuestion(CanvasResource):
    category_name = ["quiz_question", "quiz_questions",
                     "question", "questions"]
    canonical_category = 'questions'
    question_type: str
    CACHE = {}
    QUESTION_GROUP_CACHE_ID = {}
    TYPES = {}

    @classmethod
    def register_type(cls, quiz_question_type: 'Type[QuizQuestion]'):
        cls.TYPES[quiz_question_type.question_type] = quiz_question_type

    @classmethod
    def decode_question(cls, registry: Registry, question, quiz, args):
        question_type = cls.TYPES[question['question_type']]
        if args.combine:
            raw = question_type.decode_json_raw(registry, question, args)
            raw['text'] = h2m(raw['text'])
            return raw, None, None
        local = registry.get_service(args.local_service, 'local')
        title = question['question_name']
        try:
            destination_path = local.find_existing(registry, args.title,
                                                   folder_file=title)
        except FileNotFoundError:
            destination_path = local.make_markdown_filename(title)
            if args.banks:
                first_bank_path = args.banks[0].format(title=make_safe_filename(title),
                                                       id=question['id'],
                                                       quiz_title=make_safe_filename(quiz['title']),
                                                       quiz_id=quiz['id'])
                destination_path = os.path.join(first_bank_path, destination_path)
            else:
                first_bank_path = make_safe_filename(quiz['title'])
                if args.destination:
                    destination_path = os.path.join(args.destination, first_bank_path, destination_path)
                else:
                    destination_path = os.path.join(first_bank_path, destination_path)
        decoded_markdown = question_type.decode_json(registry, question, args)
        return title, destination_path, decoded_markdown

    @classmethod
    def decode_json(cls, registry: Registry, data, args):
        full_json = cls.decode_json_raw(registry, data, args)
        text = full_json.pop('text')
        return h2m(text, full_json)

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        raise NotImplementedError(data['question_type'])

    @classmethod
    def decode_question_common(self, registry: Registry, data, args):
        result = CommentedMap()
        result['title'] = data['question_name']
        if not args.combine:
            result['resource'] = 'quiz question'
        result['type'] = data['question_type']
        result['text'] = data['question_text']
        result['points'] = data['points_possible']
        result['comments'] = CommentedMap()
        if data['correct_comments_html']:
            result['comments']['if_correct'] = h2m(data['correct_comments_html'])
        if data['incorrect_comments_html']:
            result['comments']['if_incorrect'] = h2m(data['incorrect_comments_html'])
        if data['neutral_comments_html']:
            result['comments']['always'] = h2m(data['neutral_comments_html'])
        if not result['comments']:
            del result['comments']
        return result

    @classmethod
    def encode_question(cls, registry: Registry, question, args):
        question_type = cls.TYPES[question['type']]
        return question_type.encode_json_raw(registry, question, args)

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        raise NotImplementedError(data['question_type'])

    @classmethod
    def encode_question_common(cls, registry: Registry, data, args):
        if 'text' in data:
            text = m2h(data['text'])
        else:
            text = data['question_text']
        comments = data.get('comments', {})
        return {
            'question_name': data['title'],
            'question_type': data['type'],
            'question_text': text,
            'points_possible': data['points'],
            'correct_comments_html': m2h(comments.get("if_correct", "")),
            'incorrect_comments_html': m2h(comments.get("if_incorrect", "")),
            'neutral_comments_html': m2h(comments.get("always", "")),
        }

    @classmethod
    def encode_question_by_title(cls, registry: Registry, title: str, args):
        local = registry.get_service(args.local_service, 'local')
        # TODO: By default limit search to "<Quiz> Questions/" folder?
        source_path = local.find_existing(registry, args.title,
                                          folder_file=title,
                                          check_front_matter=True, top_directories=args.banks)
        decoded_markdown = local.read(source_path)
        regular, waltz, body = extract_front_matter(decoded_markdown)
        body = hide_data_in_html(regular, m2h(body))
        waltz['question_text'] = body
        return cls.encode_question(registry, waltz, args)

    @classmethod
    def _make_canvas_upload(cls, registry: Registry, question, args):
        question_type = cls.TYPES[question['question_type']]
        return question_type._make_canvas_upload_raw(registry, question, args)

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, question, args):
        raise NotImplementedError(question['question_type'])

    @classmethod
    def _make_canvas_upload_common(cls, registry: Registry, data, args):
        return {
            'question[question_type]': data['question_type'],
            'question[question_name]': data['question_name'],
            'question[question_text]': data['question_text'],
            'question[quiz_group_id]': data.get('quiz_group_id'),
            'question[points_possible]': data['points_possible'],
            'question[correct_comments_html]': data['correct_comments_html'],
            'question[incorrect_comments_html]': data['incorrect_comments_html'],
            'question[neutral_comments_html]': data['neutral_comments_html'],
        }

    @classmethod
    def _get_field(cls, data):
        return data['html'] if 'html' in data and data['html'] else data['text']