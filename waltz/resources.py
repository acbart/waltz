import re
import os
import difflib
from glob import glob

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import walk_tree, preserve_literal

from html_markdown_utilities import h2m, m2h

from waltz.yaml_setup import yaml
from waltz.canvas_tools import get

from waltz.utilities import ensure_dir, make_safe_filename

class WaltzException(Exception):
    pass

class Resource:
    canonical_category = 'unsorted'
    title = "Untitled Instance"
    
    def push(self):
        raise NotImplementedError("The push method has not been implemented.")
    
    @staticmethod
    def pull(course, resource_id):
        raise NotImplementedError("The push method has not been implemented.")
    
    def element_position(self, item):
        key, value = item
        if key in self.FIELD_ORDER:
            return self.FIELD_ORDER.index(key)
        return len(self.FIELD_ORDER)
    
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
    
    def find_on_disk(self, root):
        new_filename = make_safe_filename(self.title)+'.yaml'
        category_folder = os.path.join(root, self.canonical_category, 
                                       '**', new_filename)
        potentials = glob(category_folder)
        if not potentials:
            return os.path.join(root, self.canonical_category, new_filename)
        elif len(potentials) == 1:
            return potentials[0]
        else:
            raise ValueError("Category {} has two files with same name:\n{}"
                .format(self.canonical_category, '\n'.join(potentials)))
    
    def backup_resource(self, root):
        filename_folder = make_safe_filename(self.title)
        category_folder = os.path.join(root, 'backups', self.canonical_category,
                                       filename_folder)
        ensure_dir(category_folder)
        new_filename = make_datetime_filename() + '.yaml.gz'
        full_path = os.path.join(category_folder, new_filename)
        with gzip.open(full_path, 'wb') as out:
            out.write(self.to_yaml())
    
    @staticmethod
    def diff_type_str(self, other):
        if self != other:
            return True, "\n".join(difflib.ndiff([l.rstrip() for l in self.splitlines(1) if l.rstrip()], 
                                           [l.rstrip() for l in other.splitlines(1) if l.rstrip()]))
        return False, self
    
    @staticmethod
    def to_simple_yaml(data):
        if data is None:
            return "null"
        else:
            return str(data)
    
    @staticmethod
    def diff_type_int(self, other):
        if self != other:
            return True, "{} | {}".format(Resource.to_simple_yaml(self), 
                                    Resource.to_simple_yaml(other))
        return False, self
    
    def diff(self, other):
        differences = CommentedMap()
        unresolved = []
        for i, field in enumerate(self.FIELD_ORDER):
            diff_style = self.FIELDS[field]
            if hasattr(self, field) and hasattr(other, field):
                self_value = getattr(self, field)
                other_value = getattr(other, field)
                are_different, merged = diff_style(self_value, other_value)
                if are_different:
                    differences[field] = merged
                    differences.yaml_set_comment_before_after_key(
                        field, before="--Unresolved--"
                    )
                    unresolved.append(field)
                else:
                    differences[field] = merged
            elif hasattr(self, field):
                differences[field] = getattr(self, field)
            elif hasattr(other, field):
                differences[field] = getattr(other, field)
        return differences, unresolved
        
class TextContent(Resource):
    def __init__(self, text, template=None):
        self.template = template
        self.text = text
    def _parse_html(self):
        return 'Markdown'
    def _generate_html(self):
        return ''
        
class Page(Resource):
    def __init__(self, title, body):
        self.title = title
        self.body = body
        
class QuizQuestion(Resource):
    category_name = ["quiz_question", "quiz_questions",
                     "question", "questions"]
    canonical_category = 'questions'
    
    FIELD_ORDER = [
        "question_name", "question_type", "question_text",
        "points_possible", "correct_comments", "incorrect_comments",
        "neutral_comments"
    ]
    FIELDS = {
        "question_name": Resource.diff_type_int,
        "question_type": Resource.diff_type_int,
        "question_text": Resource.diff_type_str,
        "points_possible": Resource.diff_type_int,
        "correct_comments": Resource.diff_type_str,
        "incorrect_comments": Resource.diff_type_str,
        "neutral_comments": Resource.diff_type_str,
    }
    
    @staticmethod
    def by_name(question_name, question_bank_folder):
        for bank in iglob(question_bank_folder+'*.yaml', recursive=True):
            with open(bank) as bank_file:
                questions = yaml.load(bank_file)
                for question in questions:
                    if question['question_name'] == question_name:
                        return QuizQuestion(**question)
        raise ValueError("Question not found:"+question['question_name'])
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key == "question_text":
                self.question_text = h2m(value)
                self.question_text = re.sub(r'\n\s*\n', '\n\n', self.question_text)
                self.question_text = self.question_text.strip()
                #self.question_text = markdowner.convert(self.question_text)
            elif key in QuizQuestion.FIELDS:
                setattr(self, key, value)

class Quiz(Resource):
    category_names = ["quiz", "quizzes"]
    canonical_category = 'quizzes'
    
    def __init__(self, questions=None, question_bank_folder=None, **kwargs):
        for key, value in kwargs.items():
            if key in Quiz.FIELDS:
                setattr(self, key, value)
        self.unmatched_parameters = kwargs
        if questions is None:
            questions = []
        order = {}
        self.questions = []
        for i, question_data in enumerate(questions):
            if isinstance(question_data, str):
                # Look up in local quiz_questions
                question = QuizQuestion.by_name(question_data, question_bank_folder)
            else:
                question = QuizQuestion(**question_data)
            if 'position' in question_data:
                position = question_data['position']
                order[question] = position
            else:
                order[question] = i
            self.questions.append(question)
        self.questions.sort(key=lambda q: order[q])
    
    def convert_questions(self, value):
        return [v.to_yaml() for v in value]
    
    @staticmethod
    def diff_questions(self, other):
        merged = [o.to_yaml() for o in other]
        return False, merged
    
    @staticmethod
    def from_canvas_object(quiz_data, questions):
        quiz = Quiz(**quiz_data, questions=questions)
        return quiz
    
    @staticmethod
    def pull(course, resource_id):
        '''
        Identify the given resource on the server and create a Quiz object
        in memory.
        '''
        if resource_id.startswith("?"):
            potentials = get('quizzes', data={"search_term": resource_id[1:]},
                             course=course)
            if not potentials:
                raise WaltzException("No quizzes found for: "+resource_id)
            else:
                quiz_data = potentials[0]
        else:
            quiz_data = get('quizzes/{id}'.format(id=resource_id), course=course)
        if 'errors' in quiz_data:
            raise WaltzException("Errors in Canvas data: "+repr(quiz_data))
        quiz_id = quiz_data['id']
        questions = get('quizzes/{qid}/questions'.format(qid=quiz_id), 
                        course=course, all=True)
        return Quiz.from_canvas_object(quiz_data, questions)
    
    FIELD_ORDER = [
        "id", "title", "html_url", "mobile_url", "preview_url", "description", 
        "quiz_type", "assignment_group_id", "time_limit", "shuffle_answers", 
        "hide_results", "show_correct_answers", 
        "show_correct_answers_last_attempt", "show_correct_answers_at", 
        "hide_correct_answers_at", "one_time_results", "scoring_policy", 
        "allowed_attempts", "one_question_at_a_time", "points_possible", 
        "cant_go_back", "access_code", "ip_filter", "due_at", "unlock_at", 
        "lock_at", "published", "assignment_id", "questions"
    ]
    FIELDS = {
        "id": Resource.diff_type_int,
        "title": Resource.diff_type_str,
        "html_url": Resource.diff_type_str,
        "mobile_url": Resource.diff_type_str,
        "preview_url": Resource.diff_type_str,
        "description": Resource.diff_type_str,
        "quiz_type": Resource.diff_type_str,
        "assignment_group_id": Resource.diff_type_int,
        "time_limit": Resource.diff_type_int,
        "shuffle_answers": Resource.diff_type_int,
        "hide_results": Resource.diff_type_int,
        "show_correct_answers": Resource.diff_type_int,
        "show_correct_answers_last_attempt": Resource.diff_type_int,
        "show_correct_answers_at": Resource.diff_type_str,
        "hide_correct_answers_at": Resource.diff_type_str,
        "one_time_results": Resource.diff_type_int,
        "scoring_policy": Resource.diff_type_int,
        "allowed_attempts": Resource.diff_type_int,
        "one_question_at_a_time": Resource.diff_type_int,
        "points_possible": Resource.diff_type_int,
        "cant_go_back": Resource.diff_type_int,
        "access_code": Resource.diff_type_int,
        "ip_filter": Resource.diff_type_int,
        "due_at": Resource.diff_type_str,
        "unlock_at": Resource.diff_type_str,
        "lock_at": Resource.diff_type_str,
        "published": Resource.diff_type_int,
        "assignment_id": Resource.diff_type_int,
        "questions": diff_questions.__func__,
    }

ALL_RESOURCES = [Quiz]
RESOURCE_CATEGORIES = {}
for ResourceType in ALL_RESOURCES:
    for category in ResourceType.category_names:
        RESOURCE_CATEGORIES[category] = ResourceType
