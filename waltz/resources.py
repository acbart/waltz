import re
import os
import difflib
from glob import glob
import gzip
from collections import OrderedDict

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import walk_tree, preserve_literal

from html_markdown_utilities import h2m, m2h

from waltz.yaml_setup import yaml
from waltz.canvas_tools import get

from waltz.utilities import (ensure_dir, make_safe_filename, indent4,
                             make_datetime_filename)

class WaltzException(Exception):
    pass

class WaltzNoResourceFound(WaltzException):
    pass
    
class Convertable:
    canonical_category = 'unsorted'
    
    def to_yaml(self):
        result = CommentedMap()
        for i, field in enumerate(self.FIELD_ORDER):
            if hasattr(self, field):
                result[field] = getattr(self, field)
                if hasattr(self, 'convert_'+field):
                    converter = getattr(self, 'convert_'+field)
                    result[field] = converter(result[field])
        return result
    
    @classmethod
    def from_yaml(cls, data):
        if not data:
            return None
        return cls(**yaml.load(data))

class Resource(Convertable):
    
    title = "Untitled Instance"
    
    def push(self):
        raise NotImplementedError("The push method has not been implemented.")
    
    @staticmethod
    def pull(course, resource_id):
        raise NotImplementedError("The push method has not been implemented.")
    
    @staticmethod
    def get_names_from_json(json_data):
        for item in json_data:
            if 'name' in item:
                yield item['name']
            elif 'title' in item:
                yield item['title']
            elif 'id' in item:
                yield item['id']
            else:
                yield item
    
    @classmethod
    def get_resource(cls, course, resource_id):
        '''
        Looks for the resource on Canvas, either searching for it or looking
        it up directly.
        '''
        if resource_id.startswith("+"):
            potentials = get(cls.canonical_category,
                             data={"search_term": resource_id[1:]},
                             course=course)
            if not potentials:
                return True
            else:
                raise WaltzException("Resource {} already exists: {}".format(
                    resource_id,
                    indent4("\n".join(Resource.get_names_from_json(potentials)))
                ))
        elif resource_id.startswith("?"):
            potentials = get(cls.canonical_category,
                             data={"search_term": resource_id[1:]},
                             course=course)
            if 'errors' in potentials:
                raise WaltzException("Errors in Canvas data: "+repr(potentials))
            if not potentials:
                raise WaltzNoResourceFound("No {} resource found for: {}".format(
                    cls.canonical_category, resource_id
                ))
            elif len(potentials) > 1:
                raise WaltzNoResourceFound("Ambiguous {} resource ID: {}\nMatches:\n{}".format(
                    cls.canonical_category, resource_id,
                    indent4("\n".join(Resource.get_names_from_json(potentials)))
                ))
            else:
                return potentials[0]
        else:
            data = get('{category}/{id}'.format(category=cls.canonical_category,
                                                id=resource_id),
                       course=course)
            if 'errors' in data:
                raise WaltzNoResourceFound("Errors in Canvas data: "+repr(data))
            return data
    
    @classmethod
    def find_on_disk(cls, title, root, extension='.yaml'):
        '''
        Returns:
            bool: Whether or not this is a new file being created.
            str: The path to the file on disk.
        '''
        new_filename = make_safe_filename(title)+extension
        category_folder = os.path.join(root, cls.canonical_category, 
                                       '**', new_filename)
        potentials = glob(category_folder)
        if not potentials:
            return True, os.path.join(root, cls.canonical_category, new_filename)
        elif len(potentials) == 1:
            return False, potentials[0]
        else:
            raise ValueError("Category {} has two files with same name:\n{}"
                .format(self.canonical_category, '\n'.join(potentials)))
    
    def backup_resource(self, original, root, extension='.yaml'):
        filename_folder = make_safe_filename(self.title)
        category_folder = os.path.join(root, 'backups', self.canonical_category,
                                       filename_folder)
        ensure_dir(category_folder+"/")
        new_filename = make_datetime_filename() + extension+'.gz'
        full_path = os.path.join(category_folder, new_filename)
        with open(original, 'rb') as original_file:
            original_contents = original_file.read()
        with gzip.open(full_path, 'wb') as out:
            out.write(original_contents)
        
class HtmlContent(Resource):
    def __init__(self, text, template=None):
        self.template = template
        self.text = text
    def _parse_html(self):
        if self.text is None:
            return ""
        if self.text == "":
            return ""
        markdown = h2m(self.text)
        #markdown = re.sub(r'\n\s*\n', '\n\n', markdown)
        markdown = markdown.strip()+"\n"
        return markdown
    def _generate_html(self):
        return ''
        
class Page(Resource):
    def __init__(self, title, body):
        self.title = title
        self.body = body

class Answer(Convertable):
    FIELD_ORDER = [
        'text', 'blank_id', 'comments', 'comments_html', 'match_id', 'left',
        'right',
        'weight', 'answer_text', 'answer_weight', 'answer_comments',
        # missing word questions
        'text_after_answers',
        # matching
        'answer_match_left', 'answer_match_right',
        'matching_answer_incorrect_matches',
        # numerical
        'numerical_answer_type', 'exact', 'margin', 'approximate',
        'precision', 'start', 'end'
    ]
    
    FIELDS = {
        'text': str,
        'blank_id': str,
        'comments': str,
        'comments_html': str,
        'match_id': str,
        'left': str,
        'right': str,
        'weight': int,
        'answer_text': str, # upload to answer_html
        'answer_weight': int,
        'answer_comments': str,
        # missing word questions
        'text_after_answers': str,
        # matching
        'answer_match_left': str,
        'answer_match_right': str,
        'matching_answer_incorrect_matches': list,
        # numerical
        'numerical_answer_type': {"exact_answer", "range_answer", "precision_answer"},
        'exact': float,
        'margin': int,
        'approximate': float,
        'precision': int,
        'start': float,
        'end': float
    }
    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            if key == "answer_text":
                
                del kwargs[key]
            elif key in self.FIELDS:
                setattr(self, key, value)
                del kwargs[key]
        self.unmatched_parameters = kwargs
        print(self.unmatched_parameters)
        
class FillInMultipleBlanks(Answer):
    @staticmethod
    def from_json(answers):
        result = CommentedMap()
        for answer in answers:
            blank_id = answer['blank_id']
            text = answer['text']
            if blank_id in result:
                if isinstance(result[blank_id], str):
                    result[blank_id] = [result[blank_id]]
                result[blank_id].append(text)
            else:
                result[blank_id] = text
        return result
    
    @staticmethod
    def to_canvas(answers):
        '''answer_precision: 10
        answer_weight: 100
        numerical_answer_type: exact_answer'''
        result = {}
        for left, right in answers.items():
            result['answer_match_left'] = left
            result['answer_match_right'] = right
        return result
    
class MatchingQuestions(Answer):
    @staticmethod
    def from_json(answers):
        results = []
        for answer in answers:
            result = CommentedMap()
            result['left'] = answer['left']
            result['right'] = answer['right']
            if answer['comments']:
                result['comment'] = answer['comments']
            elif answer['comments_html']:
                result['comment'] = HtmlContent(answer['comments_html'])._parse_html()
            results.append(result)
        return results
    
    @staticmethod
    def to_canvas(answers):
        results = []
        for answer in answers:
            result = {}
            result['answer_match_left'] = answer['left']
            result['answer_match_right'] = answer['right']
            result['answer_comment_html'] = answer['comment']
            result['answer_weight'] = 100 # TODO: Unnecessary?
            result['answer_precision'] = 10 # TODO: Unnecessary?
            results.append(result)
        return results
    
class ShortAnswerQuestion(Answer):
    pass
class MultipleChoiceQuestion(Answer):
    pass
class MultipleAnswersQuestion(Answer):
    pass
class TrueFalseQuestion(Answer):
    pass
class MultipleDropDownsQuestion(Answer):
    pass
class EssayQuestion(Answer):
    pass
class TextOnlyQuestion(Answer):
    pass
        
QUESTION_TYPES = {
    'fill_in_multiple_blanks_question': FillInMultipleBlanks,
    'matching_question': MatchingQuestions,
    'short_answer_question': ShortAnswerQuestion,
    'multiple_choice_question': MultipleChoiceQuestion,
    'multiple_answers_question': MultipleAnswersQuestion,
    'true_false_question': TrueFalseQuestion,
    'multiple_dropdowns_question': MultipleDropDownsQuestion,
    'essay_question': EssayQuestion,
    'text_only_question': TextOnlyQuestion,
}

class QuizQuestion(Resource):
    category_name = ["quiz_question", "quiz_questions",
                     "question", "questions"]
    canonical_category = 'questions'
    CACHE = {}
    
    FIELD_ORDER = ["question_name", "question_type", "question_text",
    "points_possible",
    "correct_comments_html", "incorrect_comments_html", "neutral_comments_html",
    "matching_answer_incorrect_matches",
    "answers"
    ]
    
    FIELDS = {
        "question_name": str,
        "question_type": str,
        "question_text": HtmlContent,
        "points_possible": int,
        "correct_comments_html": HtmlContent,
        "incorrect_comments_html": HtmlContent,
        "neutral_comments_html": HtmlContent,
        "matching_answer_incorrect_matches": str,
        "answers": list
    }
    
    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            if self.FIELDS.get(key) == HtmlContent:
                setattr(self, key, HtmlContent(value)._parse_html())
                del kwargs[key]
            elif key in self.FIELDS:
                setattr(self, key, value)
                del kwargs[key]
        self.unmatched_parameters = kwargs
        if self.question_type == "fill_in_multiple_blanks_question":
            self.answers = FillInMultipleBlanks.from_json(self.answers)
        elif self.question_type == "matching_question":
            self.answers = MatchingQuestions.from_json(self.answers)
        else:
            answers = []
            for answer in self.answers:
                answer = QUESTION_TYPES[self.question_type](**answer)
                answers.append(answer)
            self.answers = answers
    
    def convert_answers(self, answers):
        if self.question_type == "fill_in_multiple_blanks_question":
            return answers
        elif self.question_type == "matching_question":
            return answers
        return [answer.to_yaml() for answer in answers]
    
    @staticmethod
    def load_bank(root, course, extension='.yaml'):
        category_folder = os.path.join(root, QuizQuestion.canonical_category, 
                                       '**', '*'+extension)
        QuizQuestion.CACHE[course] = {}
        for bank in glob(category_folder, recursive=True):
            with open(bank) as bank_file:
                if extension == '.yaml':
                    questions = yaml.load(bank_file)
                else:
                    raise WaltzException("Unknown extension format: "+extension)
                for question in questions:
                    question_name = question['question_name']
                    new_question = QuizQuestion(**question)
                    QuizQuestion.CACHE[course][question_name] = new_question
    
    @staticmethod
    def by_name(question_name, root, course):
        if course not in QuizQuestion.CACHE:
            QuizQuestion.load_bank(root, course)
        return QuizQuestion.CACHE[course].get(question_name, None)
        

class Quiz(Resource):
    category_names = ["quiz", "quizzes"]
    canonical_category = 'quizzes'
    
    def __init__(self, root=None, course=None, **kwargs):
        for key, value in list(kwargs.items()):
            if self.FIELDS.get(key) == HtmlContent:
                setattr(self, key, HtmlContent(value)._parse_html())
                del kwargs[key]
            elif key in self.FIELDS:
                setattr(self, key, value)
                del kwargs[key]
        self.unmatched_parameters = kwargs
        order = {}
        questions = []
        for i, question_data in enumerate(self.questions):
            if isinstance(question_data, str):
                # Look up in local quiz_questions
                question = QuizQuestion.by_name(question_data, root, course)
                if question is None:
                    raise ValueError("Question not found: "+question_data)
            else:
                question = QuizQuestion(course=course, **question_data)
            if 'position' in question_data:
                position = question_data['position']
                order[question] = position
            else:
                order[question] = i
            questions.append(question)
        self.questions = sorted(questions, key=lambda q: order[q])
    
    def convert_questions(self, questions):
        return [question.to_yaml() for question in questions]
    
    @staticmethod
    def from_canvas(root, course, resource_id):
        '''
        Identify the given resource on the canvas server and create a Quiz
        object in memory.
        '''
        quiz_data = Quiz.get_resource(course, resource_id)
        if quiz_data is True:
            return None
        questions = get('quizzes/{qid}/questions'.format(qid=quiz_data['id']), 
                        course=course, all=True)
        return Quiz(**quiz_data, questions=questions, root=root, course=course)
    
    @staticmethod
    def pull(root, course, resource_id):
        '''
        Identify the given resource on canvas and write the data to disk.
        '''
        quiz = Quiz.from_canvas(root, course, resource_id)
        is_new, path = quiz.find_on_disk(quiz.title, root)
        if is_new:
            quiz.backup_resource(path, root)
        ensure_dir(os.path.dirname(path)+"/")
        quiz_data = quiz.to_yaml()
        walk_tree(quiz_data)
        from pprint import pprint
        #pprint(quiz_data)
        with open(path, 'w') as out:
            yaml.dump(quiz_data, out)
    
    @staticmethod
    def push(root, course, resource_id):
        '''
        Find the given resource on disk and push the new version to canvas.
        '''
        quiz = Quiz.from_canvas(root, course, resource_id)
        if quiz is None:
            is_new, path = Quiz.find_on_disk(resource_id[1:], root)
        else:
            is_new, path = quiz.find_on_disk(quiz.title, root)
        if is_new:
            raise WaltzException("Quiz {} did not exist locally: {}".format(
                resource_id, path
            ))
        print(path)
        
        
    
    FIELD_ORDER = ["title", "html_url", 
    #"mobile_url", "preview_url", 
    "description", "quiz_type", 
    #"assignment_group_id",
    "time_limit", 
    "shuffle_answers", "hide_results", "show_correct_answers", 
    "show_correct_answers_last_attempt", "show_correct_answers_at", 
    "hide_correct_answers_at", "one_time_results", "scoring_policy", 
    "allowed_attempts", "one_question_at_a_time", "points_possible", 
    "cant_go_back", "access_code", "ip_filter", "due_at", "unlock_at", 
    "lock_at", "published", "questions"]
    
    FIELDS = {
        "title": str,
        "html_url": str,
        #"mobile_url": str,
        #"preview_url": str,
        "description": HtmlContent,
        "quiz_type": str,
        #"assignment_group_id": int,
        "time_limit": int,
        "shuffle_answers": bool,
        "hide_results": bool,
        "show_correct_answers": bool,
        "show_correct_answers_last_attempt": bool,
        "show_correct_answers_at": str,
        "hide_correct_answers_at": str,
        "one_time_results": bool,
        "scoring_policy": str,
        "allowed_attempts": int,
        "one_question_at_a_time": bool,
        "points_possible": int,
        "cant_go_back": bool,
        "access_code": str,
        "ip_filter": str,
        "due_at": str,
        "unlock_at": str,
        "lock_at": str,
        "published": bool,
        "questions": list,
    }

ALL_RESOURCES = [Quiz]
RESOURCE_CATEGORIES = {}
for ResourceType in ALL_RESOURCES:
    for category in ResourceType.category_names:
        RESOURCE_CATEGORIES[category] = ResourceType
