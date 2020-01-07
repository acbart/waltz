import difflib
import json
import os
import sys
from pprint import pprint

from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.resources.quizzes.quiz_group import QuizGroup
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    to_friendly_date


class Quiz(CanvasResource):
    """
    Arguments
        --combine: Keep all the questions inside the quiz
            Default: False
        --bank: Comma-separated list of locations to look for existing questions
            The first match in the list is the default place to store new questions
            Default: "./{quiz-name} Questions/"
        --use-ids: Don't rely on Question names to determine uniqueness. This is
            critical if you have questions with the same name. In general, avoid that!

    Single-file quiz
    Adjacent question files
        Local folder?
        Prefixed files?
    Question banks stored in explicit location

    When you download a quiz, it also captures the questions in the Quiz JSON.

    Are Quiz Question Names unique? No, they can't be. But by default we want
    them to be treated like they were. The user would have to intentionally say
    otherwise.

    In Canvas, Groups are attached to a question. Questions are attached to a Quiz.

    In Local, Groups are not separate but Questions are.

    If we are decoding a quiz question, we have to determine if we might be overwriting
        some other quizzes version of it. Questions remember what quizzes they came from.
        By default, if our decoding's quiz does not match, we probably shouldn't overwrite.
    """
    name = "quiz"
    name_plural = "quizzes"
    endpoint = 'quizzes/'
    category_names = ['quiz', 'quizzes']
    id = "id"

    @classmethod
    def upload(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=args.category, disambiguate=args.url)
        full_page = json.loads(raw_resource.data)
        # TODO: fix post
        canvas.api.put(cls.endpoint+"pages/{url}".format(url=full_page['title']), data={
            'wiki_page[title]': full_page['title'],
            'wiki_page[body]': full_page['body'],
            'wiki_page[published]': full_page['published']
        })

    @classmethod
    def download(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        quiz_json = cls.find(canvas, args.title)
        if quiz_json is not None:
            print("I found: ", args.title)
            decoded_json = json.loads(quiz_json)
            quiz_id = decoded_json['id']
            # Grab the questions' JSON
            questions = canvas.api.get("quizzes/{quiz_id}/questions/".format(quiz_id=quiz_id), retrieve_all=True)
            decoded_json['questions'] = questions
            # And the groups' JSON
            group_ids = {question['quiz_group_id'] for question in questions
                         if question['quiz_group_id'] is not None}
            groups = {group_id: canvas.api.get('quizzes/{quiz_id}/groups/{group_id}'.format(quiz_id=quiz_id, group_id=group_id))
                      for group_id in group_ids}
            decoded_json['groups'] = groups
            # Store the results
            quiz_json = json.dumps(decoded_json)
            registry.store_resource(canvas.name, cls.name, args.title, "", quiz_json)
            return quiz_json
        cls.find_similar(registry, canvas, args)

    @classmethod
    def decode_json(cls, registry: Registry, data: str, args):
        raw_data = json.loads(data)
        result = CommentedMap()
        result['title'] = raw_data['title']
        result['url'] = raw_data['html_url']
        result['published'] = raw_data['published']
        result['settings'] = CommentedMap()
        result['settings']['quiz_type'] = raw_data['quiz_type']
        result['settings']['points_possible'] = raw_data['points_possible']
        result['settings']['allowed_attempts'] = raw_data['allowed_attempts']
        result['settings']['scoring_policy'] = raw_data['scoring_policy']
        result['settings']['timing'] = CommentedMap()
        result['settings']['timing']['due_at'] = to_friendly_date(raw_data['due_at'])
        result['settings']['timing']['unlock_at'] = to_friendly_date(raw_data['unlock_at'])
        result['settings']['timing']['lock_at'] = to_friendly_date(raw_data['lock_at'])
        result['settings']['secrecy'] = CommentedMap()
        result['settings']['secrecy']['one_question_at_a_time'] = raw_data['one_question_at_a_time']
        result['settings']['secrecy']['shuffle_answers'] = raw_data['shuffle_answers']
        result['settings']['secrecy']['time_limit'] = raw_data['time_limit']
        result['settings']['secrecy']['cant_go_back'] = raw_data['cant_go_back']
        result['settings']['secrecy']['show_correct_answers'] = raw_data['show_correct_answers']
        result['settings']['secrecy']['show_correct_answers_last_attempt'] = raw_data['show_correct_answers_last_attempt']
        result['settings']['secrecy']['show_correct_answers_at'] = raw_data['show_correct_answers_at']
        result['settings']['secrecy']['hide_correct_answers_at'] = raw_data['hide_correct_answers_at']
        result['settings']['secrecy']['hide_results'] = raw_data['hide_results']
        result['settings']['secrecy']['one_time_results'] = raw_data['one_time_results']
        if raw_data['access_code']:
            result['settings']['secrecy']['access_code'] = raw_data['access_code']
        if raw_data['ip_filter']:
            result['settings']['secrecy']['ip_filter'] = raw_data['ip_filter']
        # Handle questions and groups
        result['questions'] = []
        available_groups = raw_data['groups']
        used_groups = {}
        for question in raw_data['questions']:
            quiz_question = QuizQuestion.decode_question(registry, question, raw_data, args)
            quiz_group_id = question.get('quiz_group_id')
            if quiz_group_id is not None:
                quiz_group_id = str(quiz_group_id) # acbart: JSON only allows string keys
                if quiz_group_id not in used_groups:
                    used_groups[quiz_group_id] = QuizGroup.decode_group(available_groups[quiz_group_id])
                    result['questions'].append(used_groups[quiz_group_id])
                used_groups[quiz_group_id]['questions'].append(quiz_question)
            else:
                result['questions'].append(quiz_question)
        return h2m(raw_data['description'], result)


    @classmethod
    def encode_json(cls, decoded_markdown):
        regular, waltz, body = extract_front_matter(decoded_markdown)
        body = hide_data_in_html(regular, m2h(body))
        return json.dumps({
            'title': waltz['title'],
            'published': waltz['published'],
            'body': body
            # TODO: Other fields
        })
