import difflib
import json
import os
import sys
from pprint import pprint

from ruamel.yaml.comments import CommentedMap

from waltz.exceptions import WaltzException
from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.resources.quizzes.quiz_group import QuizGroup
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    to_friendly_date, from_friendly_date, json_bool


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
    folder_file = 'index'

    @classmethod
    def find(cls, canvas, title):
        # TODO: Change canvas -> registry, title -> args
        resources = canvas.api.get(cls.endpoint, retrieve_all=True, data={"search_term": title})
        for resource in resources:
            if resource['title'] == title:
                quiz = canvas.api.get(cls.endpoint + str(resource[cls.id]))
                # Grab the questions' JSON
                quiz['questions'] = canvas.api.get("quizzes/{quiz_id}/questions/".format(quiz_id=quiz['id']), retrieve_all=True)
                # And the groups' JSON
                group_ids = {question['quiz_group_id'] for question in quiz['questions']
                             if question['quiz_group_id'] is not None}
                quiz['groups'] = {group_id: canvas.api.get(
                    'quizzes/{quiz_id}/groups/{group_id}'.format(quiz_id=quiz['id'], group_id=group_id))
                          for group_id in group_ids}
                return quiz
        return None

    @classmethod
    def upload(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        # Get the local version
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=args.category, disambiguate=args.id)
        local_quiz = json.loads(raw_resource.data)
        # Get the remote version
        remote_quiz = cls.find(canvas, args.title)
        # Either put or post the quiz
        if remote_quiz is None:
            cls.upload_new(registry, local_quiz, args)
        else:
            cls.upload_edit(registry, remote_quiz, local_quiz, args)

    @classmethod
    def upload_new(cls, registry: Registry, local_quiz, args):
        canvas = registry.get_service(args.service, "canvas")
        quiz_data = cls._make_canvas_upload(registry, local_quiz, args)
        created_quiz = canvas.api.post('quizzes/', data=quiz_data)
        if 'errors' in created_quiz:
            pprint(created_quiz['errors'])
            raise WaltzException("Error loading data, see above.")
        print("Created quiz", local_quiz['title'], "on canvas")
        # Create the groups
        group_name_to_id = {}
        for group in local_quiz['groups'].values():
            group_data = QuizGroup._make_canvas_upload(registry, group, args)
            created_group = canvas.api.post('quizzes/{quiz_id}/groups'.format(quiz_id=created_quiz['id']),
                                            data=group_data)
            created_group = created_group['quiz_groups'][0]  # acbart: Weird response type
            # acbart: Okay because names are strings and IDs are ints
            group_name_to_id[created_group['name']] = created_group['id']
            group_name_to_id[created_group['id']] = created_group['id']
        if local_quiz['groups']:
            print("Created quiz", local_quiz['title'], "groups on canvas")
        # Create the questions
        for question in local_quiz['questions']:
            if 'quiz_group_id' in question and question['quiz_group_id'] is not None:
                question['quiz_group_id'] = group_name_to_id[question['quiz_group_id']]
            question_data = QuizQuestion._make_canvas_upload(registry, question, args)
            created_question = canvas.api.post('quizzes/{quiz_id}/questions'.format(quiz_id=created_quiz['id']),
                                               data=question_data)
        print("Created quiz", local_quiz['title'], "questions on canvas")


    @classmethod
    def upload_edit(cls, registry: Registry, old_quiz, new_quiz, args):
        canvas = registry.get_service(args.service, "canvas")
        quiz_id = old_quiz['id']
        # Edit the quiz on canvas
        quiz_data = cls._make_canvas_upload(registry, new_quiz, args)
        canvas.api.put('quizzes/{quiz_id}'.format(quiz_id=quiz_id), data=quiz_data)
        print("Updated quiz", old_quiz['title'], "on canvas")
        # Make a map of the old groups' names/ids to the groups
        old_group_map = {}
        for group in old_quiz['groups'].values():
            old_group_map[group['name']] = group
            old_group_map[group['id']] = group
        # Update groups with the same name and create new ones
        used_groups = {}
        for group in new_quiz['groups'].values():
            group_data = QuizGroup._make_canvas_upload(registry, group, args)
            if group['name'] in old_group_map:
                canvas_group = old_group_map[group['name']]
                canvas_group = canvas.api.put('quizzes/{quiz_id}/groups/{group_id}'.format(quiz_id=quiz_id,
                                                                                           group_id=canvas_group['id']),
                                              data=group_data)
            else:
                canvas_group = canvas.api.post('quizzes/{quiz_id}/groups'.format(quiz_id=quiz_id),
                                               data=group_data)
            canvas_group = canvas_group['quiz_groups'][0] # acbart: Weird response type
            used_groups[canvas_group['name']] = canvas_group
            used_groups[canvas_group['id']] = canvas_group
        if new_quiz['groups']:
            print("Updated quiz", old_quiz['title'], "groups on canvas")
        # Delete any groups that no longer have a reference
        for old_group in old_quiz['groups'].values():
            if old_group['id'] not in used_groups:
                canvas.api.delete('quizzes/{quiz_id}/groups/{group_id}'.format(quiz_id=quiz_id,
                                                                               group_id=old_group['id']))
                print("Deleted question group", old_group['name'], " (ID: {})".format(old_group['id']))
        # Push all the questions
        name_map = {q['question_name']: q for q in old_quiz['questions']}
        used_questions = {}
        for new_question in new_quiz['questions']:
            if new_question.get('quiz_group_id') is not None:
                new_question['quiz_group_id'] = used_groups[new_question['quiz_group_id']]['id']
            question_data = QuizQuestion._make_canvas_upload(registry, new_question, args)
            if new_question['question_name'] in name_map:
                canvas_question = name_map[new_question['question_name']]
                canvas_question = canvas.api.put('quizzes/{quiz_id}/questions/{question_id}'.format(quiz_id=quiz_id,
                                                                                                    question_id=canvas_question['id']),
                                                 data=question_data)
            else:
                canvas_question = canvas.api.post('quizzes/{quiz_id}/questions'.format(quiz_id=quiz_id),
                                                  data=question_data)
            used_questions[canvas_question['id']] = canvas_question
        print("Updated quiz", old_quiz['title'], "questions on canvas")
        # Delete any old questions
        for question in old_quiz['questions']:
            if question['id'] not in used_questions:
                canvas.api.delete('quizzes/{quiz_id}/questions/{question_id}'.format(quiz_id=quiz_id,
                                                                                     question_id=question['id']))
                print("Deleted question", question.get('name', "NO NAME"), " (ID: {})".format(question['id']))

    REQUIRED_UPLOAD_FIELDS = ['title', 'description', 'quiz_type']
    OPTIONAL_UPLOAD_FIELDS = ['time_limit', 'shuffle_answers', 'hide_results',
                              'show_correct_answers', 'show_correct_answers_last_attempt',
                              'show_correct_answers_at', 'hide_correct_answers_at',
                              'allowed_attempts', 'scoring_policy', 'one_question_at_a_time',
                              'cant_go_back', 'access_code', 'ip_filter', 'due_at',
                              'lock_at', 'unlock_at', 'published', 'one_time_results']

    @classmethod
    def _make_canvas_upload(cls, registry: Registry, quiz, args):
        payload = {'quiz[notify_of_update]': 'false'}
        for field in cls.REQUIRED_UPLOAD_FIELDS:
            payload["quiz[{}]".format(field)] = quiz[field]
        for field in cls.OPTIONAL_UPLOAD_FIELDS:
            if field in quiz and quiz[field] not in (None, ""):
                payload["quiz[{}]".format(field)] = quiz[field]
        return payload

    @classmethod
    def decode_json(cls, registry: Registry, data: str, args):
        raw_data = json.loads(data)
        result = CommentedMap()
        result['title'] = raw_data['title']
        result['resource'] = 'quiz'
        result['url'] = raw_data['html_url']
        result['published'] = raw_data['published']
        result['settings'] = CommentedMap()
        result['settings']['quiz_type'] = raw_data['quiz_type']
        if raw_data.get('points_possible') is not None:
            result['settings']['points_possible'] = raw_data['points_possible']
        result['settings']['allowed_attempts'] = raw_data['allowed_attempts']
        result['settings']['scoring_policy'] = raw_data['scoring_policy']
        result['settings']['timing'] = CommentedMap()
        result['settings']['timing']['due_at'] = to_friendly_date(raw_data['due_at'])
        result['settings']['timing']['unlock_at'] = to_friendly_date(raw_data['unlock_at'])
        result['settings']['timing']['lock_at'] = to_friendly_date(raw_data['lock_at'])
        result['settings']['secrecy'] = CommentedMap()
        result['settings']['secrecy']['shuffle_answers'] = raw_data['shuffle_answers']
        result['settings']['secrecy']['time_limit'] = raw_data['time_limit']
        result['settings']['secrecy']['one_question_at_a_time'] = raw_data['one_question_at_a_time']
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
        extra_files = []
        for question in raw_data['questions']:
            quiz_question, destination_path, full_body = QuizQuestion.decode_question(registry, question, raw_data, args)
            if destination_path is not None:
                extra_files.append((destination_path, full_body))
            quiz_group_id = question.get('quiz_group_id')
            if quiz_group_id is not None:
                quiz_group_id = str(quiz_group_id) # acbart: JSON only allows string keys
                if quiz_group_id not in used_groups:
                    used_groups[quiz_group_id] = QuizGroup.decode_group(available_groups[quiz_group_id])
                    result['questions'].append(used_groups[quiz_group_id])
                used_groups[quiz_group_id]['questions'].append(quiz_question)
            else:
                result['questions'].append(quiz_question)
        return h2m(raw_data['description'], result), extra_files

    @classmethod
    def encode_json(cls, registry: Registry, data, args):
        regular, waltz, body = extract_front_matter(data)
        settings = waltz.get('settings', {})
        timing = settings.get('timing', {})
        secrecy = settings.get('secrecy', {})
        body = hide_data_in_html(regular, m2h(body))
        questions = []
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
            'one_question_at_a_time': int(secrecy.get('one_question_at_a_time', 0)),
            'shuffle_answers': int(secrecy.get('shuffle_answers', 0)),
            'time_limit': secrecy.get('time_limit'),
            'cant_go_back': int(secrecy.get('cant_go_back', 0)),
            'show_correct_answers': int(secrecy.get('show_correct_answers', 1)),
            'show_correct_answers_last_attempt': secrecy.get('show_correct_answers_last_attempt'),
            'show_correct_answers_at': secrecy.get('show_correct_answers_at'),
            'hide_correct_answers_at': secrecy.get('hide_correct_answers_at'),
            'hide_results': secrecy.get('hide_results'),
            'one_time_results': int(secrecy.get('one_time_results', 0)),
            'access_code': secrecy.get('access_code'),
            'ip_filter': secrecy.get('ip_filter'),
            # Questions and Groups
            'questions': questions,
            'groups': groups
        })

    @classmethod
    def diff_extra_files(cls, registry: Registry, data, args):
        local = registry.get_service(args.local_service, 'local')
        regular, waltz, body = extract_front_matter(data)
        for question in waltz['questions']:
            if isinstance(question, str):
                destination_path = local.find_existing(registry, args.title,
                                                       folder_file=question,
                                                       check_front_matter=True,
                                                       top_directories=args.banks)
                yield destination_path, local.read(destination_path)
            elif 'group' in question:
                for inner_question in question['questions']:
                    if isinstance(inner_question, str):
                        destination_path = local.find_existing(registry, args.title,
                                                               folder_file=inner_question)
                        yield destination_path, local.read(destination_path)
