import json
import os
from typing import Type

from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m
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
        if question['question_type'] not in cls.TYPES:
            # TODO: Ensure that this isn't needed
            return "NotImplementedYet"
        question_type = cls.TYPES[question['question_type']]
        if args.combine:
            return question_type.decode_json_raw(registry, question, args)
        local = registry.get_service(args.local_service, 'local')
        title = question['question_name']
        try:
            destination_path = local.find_existing(registry, title)
        except FileNotFoundError:
            destination_path = local.make_markdown_filename(title)
            if args.banks:
                first_bank_path = args.banks[0].format(title=make_safe_filename(title),
                                                       id=question['id'],
                                                       quiz_title=make_safe_filename(quiz['title']),
                                                       quiz_id=quiz['id'])
                destination_path = os.path.join(first_bank_path, destination_path)
            else:
                first_bank_path = make_safe_filename('{quiz_title} Questions'.format(quiz_title=quiz['title']))
                if args.destination:
                    destination_path = os.path.join(args.destination, first_bank_path, destination_path)
                else:
                    destination_path = os.path.join(first_bank_path, destination_path)
        decoded_markdown = question_type.decode_json(registry, question, args)
        local.write(destination_path, decoded_markdown)
        return title

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
        result['type'] = data['question_type']
        result['text'] = h2m(data['question_text'])
        result['points'] = data['points_possible']
        result['comments'] = CommentedMap()
        if data['correct_comments_html']:
            result['if_correct'] = h2m(data['correct_comments_html'])
        if data['incorrect_comments_html']:
            result['if_incorrect'] = h2m(data['incorrect_comments_html'])
        if data['neutral_comments_html']:
            result['always'] = h2m(data['neutral_comments_html'])
        if not result['comments']:
            del result['comments']
        return result

    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            setattr(self, key, value)
            del kwargs[key]
        self.bank_source = False
        return

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        else:
            return vars(self) == vars(other)

    def to_public(self, force=False):
        if self.bank_source and not force:
            return self.question_name
        result = CommentedMap()
        result['question_name'] = self.question_name
        result['question_type'] = self.question_type
        result['question_text'] = h2m(self.question_text)
        if self.quiz_group_name:
            result['group'] = self.quiz_group_name
        result['points_possible'] = self.points_possible
        return result



    def to_json(self, course, resource_id):
        return {
            'question[question_type]': self.question_type,
            'question[question_name]': self.question_name,
            'question[question_text]': self.question_text,
            'question[quiz_group_id]': self.quiz_group_id,
            'question[points_possible]': self.points_possible,
            'question[correct_comments_html]': self.correct_comments_html,
            'question[incorrect_comments_html]': self.incorrect_comments_html,
            'question[neutral_comments_html]': self.neutral_comments_html,
        }

    @classmethod
    def _lookup_quiz_id(cls, quiz_id, group_id, course):
        if (quiz_id, group_id) in cls.QUESTION_GROUP_CACHE_ID:
            return cls.QUESTION_GROUP_CACHE_ID[(quiz_id, group_id)]
        group = get('quizzes/{qid}/groups/{gid}'.format(qid=quiz_id,
                                                        gid=group_id),
                    course=course.course_name)
        cls.QUESTION_GROUP_CACHE_ID[id] = group
        return group

    @classmethod
    def from_json(cls, course, json_data, group_map):
        # TODO: Match up to bank question and diff
        question_name = json_data['question_name']
        question_type = json_data['question_type']
        bank_question = cls.by_name(question_name, course)
        actual_class = QUESTION_TYPES[question_type]
        if json_data['quiz_group_id']:
            group = group_map[json_data['quiz_group_id']]
        else:
            group = None
        new_question = actual_class(course=course, quiz_group_name=group,
                                    **json_data)

        # Use cached version
        if new_question == bank_question:
            return bank_question

        if bank_question is not None:
            QuizQuestion.update_bank(course, question_name,
                                     bank_question.bank_source, new_question)

        return new_question

    @classmethod
    def update_bank(cls, course, question_name, bank_source, new_question):
        course.backup_bank(bank_source)
        course_cache = cls.CACHE[course.course_name]
        course_cache[question_name] = new_question
        # Grab the names of the old questions
        kept_question_names = []
        with open(bank_source) as bank_file:
            questions = yaml.load(bank_file)
            for question in questions:
                question_name = question['question_name']
                kept_question_names.append(['question_name'])
        # Get the actual up-to-date questions
        questions = [course_cache[name].to_disk(force=True)
                     for name in kept_question_names]
        # Dump them back into the file
        walk_tree(questions)
        with open(bank_source, 'w') as bank_file:
            yaml.dump(questions, bank_file)

    def _custom_from_disk(cls, yaml_data):
        pass

    @classmethod
    def from_disk(cls, course, yaml_data, resource_id):
        question_type = yaml_data['question_type']
        actual_class = QUESTION_TYPES[question_type]
        yaml_data['question_text'] = m2h(yaml_data['question_text'])
        # Fix simplifications of comments
        for label in ['correct_comments', 'incorrect_comments', 'neutral_comments']:
            yaml_data[label + "_html"] = m2h(yaml_data.pop(label, ""))
        yaml_data['quiz_group_id'] = yaml_data.pop('group', None)
        # Fix answers
        actual_class._custom_from_disk(yaml_data)
        # Load the appropriate type
        if isinstance(yaml_data, str):
            return QuizQuestion.by_name(yaml_data['question_name'], course)
        else:
            return actual_class(course=course, **yaml_data)

    def push(self, course, quiz_id, name_map, json_data):
        '''
        Get all the questions in this quiz
        If this name is already in the quiz, then update it's compnents.
        Otherwise, create a new element.
        '''
        if self.question_name in name_map:
            id = name_map[self.question_name]
            result = put("quizzes/{quiz}/questions/{question}/".format(
                quiz=quiz_id, question=id
            ), data=json_data, course=course.course_name)
        else:
            result = post("quizzes/{quiz}/questions/".format(
                quiz=quiz_id
            ), data=json_data, course=course.course_name)

