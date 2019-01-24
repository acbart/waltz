import re
import os
import difflib
from glob import glob
import gzip
import json
from collections import OrderedDict
from pprint import pprint

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import walk_tree, preserve_literal

from html_markdown_utilities import h2m, m2h

from waltz.yaml_setup import yaml
from waltz.canvas_tools import get, put, post

from waltz.utilities import (ensure_dir, make_safe_filename, indent4,
                             make_datetime_filename)
                             
'''
`Course` has a 

ResourceID is instantly matched to
    a CanvasPath
    a DiskPath



`ResourceType` can be dumped to `Disk<ResourceType>`
    @ResourceType.to_disk(ResourceID)
        Backups `.yaml` on disk automatically

`Disk<ResourceType>` can be loaded into a `ResourceType` object
    @Course.from_disk(ResourceID) -> @ResourceType
`ResourceType` object can be converted to a `Canvas<ResourceType>`
    @ResourceType.to_json() -> JSON
JSON data can be pushed to Canvas
    @Course.push(ResourceID, JSON)
        Backups `.json` on disk automatically
'''

class WaltzException(Exception):
    pass

class WaltzNoResourceFound(WaltzException):
    pass

class ResourceID:
    def __init__(self, course, raw):
        self.course = course
        self.raw = raw
        self._parse_type()
        self._get_canvas_data()
        self._get_disk_path()
    
    def _parse_type(self):
        self.category, action = self.raw.split("/", 1)
        self.category = self.category.lower()
        self.command, self.name = action[0], action[1:]
        if self.category not in RESOURCE_CATEGORIES:
            raise WaltzException("Category {} not found (full Resource ID: {!r})".format(
                self.category, self.raw
            ))
        self.resource_type = RESOURCE_CATEGORIES[self.category]
    
    def _new_canvas_resource(self):
        potentials = self.resource_type.find_resource_on_canvas(self.course, self.name)
        if not potentials:
            return True
        else:
            raise WaltzException("Resource {} already exists: {}".format(
                resource_id,
                indent4("\n".join(Resource.get_names_from_json(potentials)))
            ))
    
    def _find_canvas_resource(self):
        potentials = self.resource_type.find_resource_on_canvas(self.course, self.name)
        if not potentials:
            raise WaltzNoResourceFound("No {} resource found for: {}".format(
                self.resource_type.canvas_name, self.raw
            ))
        elif len(potentials) > 1:
            raise WaltzNoResourceFound("Ambiguous {} resource ID: {}\nMatches:\n{}".format(
                self.resource_type.canvas_name, self.raw,
                indent4("\n".join(self.resource_type.get_names_from_json(potentials)))
            ))
        else:
            return potentials[0]
    
    def _get_canvas_resource(self):
        return self.resource_type.get_resource_on_canvas(self.course, self.name)
    
    def _get_canvas_data(self):
        '''
        Looks for the resource on Canvas, either searching for it or looking
        it up directly.
        '''
        if self.command.startswith("+"):
            self.canvas_data = self._new_canvas_resource()
        elif self.command.startswith("?"):
            self.canvas_data = self._find_canvas_resource()
        elif self.command.startswith(":"):
            self.canvas_data = self._get_canvas_resource()
        else:
            raise WaltzException("Unknown command: "+repr(self.command))
        self._parse_canvas_data()
    
    def _parse_canvas_data(self):
        if self.canvas_data is True:
            self.canvas_title = self.name
            self.canvas_id = None
        else:
            self.canvas_title = self.resource_type.identify_title(self.canvas_data)
            self.canvas_id = self.canvas_data['id']
    
    def _get_disk_path(self):
        self.filename = make_safe_filename(self.canvas_title)+'.yaml'
        self.is_new, self.path = self.resource_type.find_resource_on_disk(self.course.root_directory, self.filename)


class Course:
    def __init__(self, root_directory, course_name):
        self.root_directory = root_directory
        self.backups = os.path.join(root_directory, 'backups')
        self.course_name = course_name
    
    def pull(self, resource_id):
        '''
        Args:
            resource_id (ResourceID): The resource ID to pull from Canvas.
        Returns:
            JSON: The JSON representation of the object straight from canvas.
        '''
        return resource_id.canvas_data
    
    def to_disk(self, resource_id, resource):
        resource_data = resource.to_disk(resource_id)
        walk_tree(resource_data)
        with open(resource_id.path, 'w') as out:
            yaml.dump(resource_data, out)
    
    def from_disk(self, resource_id):
        '''
        Args:
            resource_id (ResourceID): The resource ID to load in.
        Returns:
            Resource: The formatted resource object
        '''
        if not os.path.exists(resource_id.path):
            return None
        with open(resource_id.path) as resource_file:
            resource_yaml = yaml.load(resource_file)
        return resource_id.resource_type.from_disk(self, resource_yaml)
    
    def from_json(self, resource_id, json_data):
        '''`Canvas<ResourceType>` can be converted to `ResourceType`
            @Course.from_json(ResourceID, JSON) -> @ResourceType'''
        return resource_id.resource_type.from_json(self, json_data)
    
    def to_json(self, resource_id, resource):
        return resource.to_json(self, resource_id)
    
    def push(self, resource_id, json_data):
        if resource_id.canvas_data is True:
            id = None
        else:
            id = resource_id.canvas_data['id']
        rtype = resource_id.resource_type
        resource_id.canvas_data =  rtype.put_on_canvas(self.course_name, id, json_data)
        resource_id._parse_canvas_data()
    
    def backup_json(self, resource_id, json_data):
        resource_path = resource_id.resource_type.identify_filename(resource_id.filename)
        backup_directory = os.path.join(self.backups, resource_path)
        ensure_dir(backup_directory+"/")
        timestamped_filename = make_datetime_filename() + '.json' +'.gz'
        backup_path = os.path.join(backup_directory, timestamped_filename)
        with gzip.open(backup_path, 'wt', encoding="utf-8") as out:
            json.dump(json_data, out)
    
    def backup_resource(self, resource_id):
        resource_path = resource_id.resource_type.identify_filename(resource_id.filename)
        backup_directory = os.path.join(self.backups, resource_path)
        ensure_dir(backup_directory+"/")
        timestamped_filename = make_datetime_filename() + '.yaml' +'.gz'
        backup_path = os.path.join(backup_directory, timestamped_filename)
        if not os.path.exists(resource_id.path):
            return
        with open(resource_id.path, 'rb') as original_file:
            contents = original_file.read()
        with gzip.open(backup_path, 'wb') as out:
            out.write(contents)
    
    def backup_bank(self, bank_source):
        backup_directory = os.path.join(self.backups, bank_source)
        ensure_dir(backup_directory+"/")
        timestamped_filename = make_datetime_filename() + '.yaml' +'.gz'
        backup_path = os.path.join(backup_directory, timestamped_filename)
        with open(resource_id.path, 'rb') as original_file:
            contents = original_file.read()
        with gzip.open(backup_path, 'wb') as out:
            out.write(contents)

class Resource:
    title = "Untitled Instance"
    
    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            setattr(self, key, value)
            del kwargs[key]
        self.unmatched_parameters = kwargs
    
    def to_json(self, course, resource_id):
        raise NotImplementedError("The to_json method has not been implemented.")
    
    def to_disk(self):
        raise NotImplementedError("The to_disk method has not been implemented.")
        
    @classmethod
    def from_json(cls):
        raise NotImplementedError("The from_json method has not been implemented.")
    
    @classmethod
    def from_disk(cls):
        raise NotImplementedError("The from_disk method has not been implemented.")
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        pass
    
    def extra_push(self, course, resource_id):
        pass
    
    @classmethod
    def extra_pull(cls, course, resource_id):
        pass
    
    @classmethod
    def put_on_canvas(cls, course_name, id, json_data):
        if id is None:
            verb, endpoint = post, cls.canvas_name
        else:
            verb, endpoint = put, "{}/{}".format(cls.canvas_name, id)
        result = verb(endpoint, data=json_data, course=course_name)
        if 'errors' in result:
            raise WaltzException("Errors in Canvas data: "+repr(results))
        return result
    
    @classmethod
    def find_resource_on_canvas(cls, course, resource_name):
        results = get(cls.canvas_name, params={"search_term": resource_name},
                      course=course.course_name)
        if 'errors' in results:
            raise WaltzException("Errors in Canvas data: "+repr(results))
        return results
    
    @classmethod
    def get_resource_on_canvas(cls, course, resource_name):
        data = get('{}/{}'.format(cls.canvas_name, resource_name),
                   course=course.course_name)
        if 'errors' in data:
            raise WaltzNoResourceFound("Errors in Canvas data: "+repr(data))
        return data
    
    @classmethod
    def find_resource_on_disk(cls, root, filename):
        search_path = os.path.join(root, cls.canonical_category, '**', filename)
        potentials = glob(search_path, recursive=True)
        if not potentials:
            return True, os.path.join(root, cls.canonical_category, filename)
        elif len(potentials) == 1:
            return False, potentials[0]
        else:
            raise ValueError("Category {} has two files with same name:\n{}"
                .format(self.canonical_category, '\n'.join(potentials)))
    
    @classmethod
    def identify_filename(cls, filename):
        return os.path.join(cls.canonical_category, filename)
    
    @classmethod
    def identify_title(cls, json_data):
        return json_data[cls.canvas_title_field]
    
    @staticmethod
    def _get_first_field(data, *fields, default="", convert=False):
        for field in fields:
            if field in data and data[field]:
                value = data[field]
                if convert and "html" in field:
                    value = convert(value)
                return value
        return default
        
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

class QuizQuestion(Resource):
    category_name = ["quiz_question", "quiz_questions",
                     "question", "questions"]
    canonical_category = 'questions'
    CACHE = {}
    
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
    
    def to_disk(self, force=False):
        if self.bank_source and not force:
            return self.question_name
        result = CommentedMap()
        result['question_name'] = self.question_name
        result['question_type'] = self.question_type
        result['question_text'] = h2m(self.question_text)
        result['points_possible'] = self.points_possible
        if self.correct_comments_html:
            result['correct_comments'] = h2m(self.correct_comments_html)
        if self.incorrect_comments_html:
            result['incorrect_comments'] = h2m(self.incorrect_comments_html)
        if self.neutral_comments_html:
            result['neutral_comments'] = h2m(self.neutral_comments_html)
        return result
    
    def to_json(self, course, resource_id):
        return {
            'question[question_type]': self.question_type,
            'question[question_name]': self.question_name,
            'question[question_text]': self.question_text,
            'question[points_possible]': self.points_possible,
            'question[correct_comments_html]': self.correct_comments_html,
            'question[incorrect_comments_html]': self.incorrect_comments_html,
            'question[neutral_comments_html]': self.neutral_comments_html,
        }
    
    @classmethod
    def from_json(cls, course, json_data):
        # TODO: Match up to bank question and diff
        question_name = json_data['question_name']
        question_type = json_data['question_type']
        bank_question = cls.by_name(question_name, course)
        actual_class = QUESTION_TYPES[question_type]
        new_question = actual_class(course=course, **json_data)
        
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
            yaml.dump(questions, out)
    
    def _custom_from_disk(cls, yaml_data):
        pass
    
    @classmethod
    def from_disk(cls, course, yaml_data):
        question_type = yaml_data['question_type']
        actual_class = QUESTION_TYPES[question_type]
        yaml_data['question_text'] = m2h(yaml_data['question_text'])
        # Fix simplifications of comments
        for label in ['correct_comments', 'incorrect_comments', 'neutral_comments']:
            yaml_data[label+"_html"] = yaml_data.pop(label, "")
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
    
    @staticmethod
    def load_bank(course):
        category_folder = os.path.join(course.root_directory,
                                       QuizQuestion.canonical_category, 
                                       '**', '*.yaml')
        QuizQuestion.CACHE[course.course_name] = {}
        for bank in glob(category_folder, recursive=True):
            with open(bank) as bank_file:
                questions = yaml.load(bank_file)
                for question in questions:
                    question_name = question['question_name']
                    new_question = QuizQuestion.from_disk(question)
                    new_question.bank_source = os.path.dirname(bank)
                    QuizQuestion.CACHE[course.course_name][question_name] = new_question
    
    @staticmethod
    def by_name(question_name, course):
        if course.course_name not in QuizQuestion.CACHE:
            QuizQuestion.load_bank(course)
        return QuizQuestion.CACHE[course.course_name].get(question_name, None)

class MultipleChoiceQuestion(QuizQuestion):
    question_type = 'multiple_choice_question'
    
    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = []
        for answer in self.answers:
            a = CommentedMap()
            text = self._get_first_field(answer, 'html', 'text', convert=h2m)
            if answer['weight']:
                a['correct'] = text
            else:
                a['wrong'] = text
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'weight': 100 if 'correct' in answer else 0,
             'html': m2h(answer['correct'] if 'correct' in answer
                     else answer['wrong'])}
            for answer in yaml_data['answers']]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_html]"] = self._get_first_field(answer, 'html', 'text')
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = answer['weight']
        return result
        
class TrueFalseQuestion(QuizQuestion):
    question_type = 'true_false_question'
    
    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        for answer in self.answers:
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if answer['text'] == 'True':
                result['answer'] = True if answer['weight'] else False
                if comment:
                    result['true_comment'] = comment
            else:
                result['false_comment'] = comment
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(yaml_data.get('true_comment', "")),
             'weight': 100 if yaml_data['answer'] else 0,
             'text': 'True'},
            {'comments_html': m2h(yaml_data.get('false_comment', "")),
             'weight': 100 if not yaml_data['answer'] else 0,
             'text': 'False'}]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_text]"] = answer['text']
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = answer['weight']
        return result

class ShortAnswerQuestion(QuizQuestion):
    question_type = 'short_answer_question'

    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = []
        for answer in self.answers:
            a = CommentedMap()
            a['text'] = answer['text']
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['text']}
            for answer in yaml_data['answers']]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_text]"] = answer['text']
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = 100
        return result
        
class FillInMultipleBlanks(QuizQuestion):
    question_type = 'fill_in_multiple_blanks_question'

    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = CommentedMap()
        for answer in self.answers:
            blank_id = answer['blank_id']
            if blank_id not in result['answers']:
                result['answers'][blank_id] = []
            a = CommentedMap()
            a['text'] = answer['text']
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'][blank_id].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['text'],
             'blank_id': blank_id}
            for blank_id, answers in yaml_data['answers'].items()
            for answer in answers]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_text]"] = answer['text']
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = 100
            result[base+"[blank_id]"] = answer['blank_id']
        return result

class MultipleAnswersQuestion(QuizQuestion):
    question_type = 'multiple_answers_question'
    
    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = []
        for answer in self.answers:
            a = CommentedMap()
            text = self._get_first_field(answer, 'html', 'text', convert=h2m)
            if answer['weight']:
                a['correct'] = text
            else:
                a['wrong'] = text
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'weight': 100 if 'correct' in answer else 0,
             'html': m2h(answer['correct'] if 'correct' in answer
                     else answer['wrong'])}
            for answer in yaml_data['answers']]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_html]"] = self._get_first_field(answer, 'html', 'text')
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = answer['weight']
        return result

class MultipleDropDownsQuestion(QuizQuestion):
    question_type = 'multiple_dropdowns_question'

    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = CommentedMap()
        for answer in self.answers:
            blank_id = answer['blank_id']
            if blank_id not in result['answers']:
                result['answers'][blank_id] = []
            a = CommentedMap()
            text = answer['text']
            if answer['weight']:
                a['correct'] = text
            else:
                a['wrong'] = text
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'][blank_id].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['correct'] if 'correct' in answer
                     else answer['wrong'],
             'weight': 100 if 'correct' in answer else 0,
             'blank_id': blank_id}
            for blank_id, answers in yaml_data['answers'].items()
            for answer in answers]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_text]"] = answer['text']
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[answer_weight]"] = answer['weight']
            result[base+"[blank_id]"] = answer['blank_id']
        return result

class MatchingQuestions(QuizQuestion):
    question_type = 'matching_question'

    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result["incorrect_matches"] = self.matching_answer_incorrect_matches
        result['answers'] = []
        for answer in self.answers:
            a = CommentedMap()
            a['left'] = answer['left']
            a['right'] = answer['right']
            if 'comments' in answer and answer['comments']:
                a['comment'] = answer['comments']
            elif 'comments_html' in answer and answer['comments_html']:
                a['comment'] = h2m(answer['comments_html'])
            result['answers'].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['matching_answer_incorrect_matches'] = yaml_data.pop('incorrect_matches')
        yaml_data['answers'] = [{'comments_html': m2h(answer.get('comment', '')),
                                 'left': answer['left'],
                                 'right': answer['right']}
                                for answer in yaml_data['answers']]
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        result['question[matching_answer_incorrect_matches]'] = self.matching_answer_incorrect_matches
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_match_left]"] = answer['left']
            result[base+"[answer_match_right]"] = answer['right']
            result[base+"[answer_comment_html]"] = answer['comments_html']
            result[base+"[answer_weight]"] = 100 # TODO: Unnecessary?
            result[base+"[answer_precision]"] = 10 # TODO: Unnecessary?
        return result

class NumericalQuestion(QuizQuestion):
    question_type = 'multiple_answers_question'
    
    def to_disk(self, force=False):
        result = QuizQuestion.to_disk(self, force)
        result['answers'] = []
        for answer in self.answers:
            a = CommentedMap()
            if answer['numerical_answer_type'] == 'exact_answer':
                a['exact'] = answer['exact']
                a['margin'] = answer['margin']
            elif answer['numerical_answer_type'] == 'range_answer':
                a['start'] = answer['start']
                a['end'] = answer['end']
            elif answer['numerical_answer_type'] == 'precision_answer':
                a['precision'] = answer['precision']
                a['approximate'] = answer['approximate']
            comment = self._get_first_field(answer, 'comments_html', 'comments', convert=h2m)
            if comment:
                a['comment'] = comment
            result['answers'].append(a)
        return result
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        answers = []
        for answer in yaml_data['answers']:
            numerical_answer_type = ('exact_answer' if 'exact' in answer else
                                     'range_answer' if 'start' in answer else
                                     'precision_answer')
            a = {'comments_html': m2h(answer.get('comment', "")),
                 'numerical_answer_type': numerical_answer_type}
            if numerical_answer_type == 'exact_answer':
                a['exact'] = answer['exact']
                a['margin'] = answer['margin']
            elif numerical_answer_type == 'range_answer':
                a['start'] = answer['start']
                a['end'] = answer['end']
            elif numerical_answer_type == 'precision_answer':
                a['precision'] = answer['precision']
                a['approximate'] = answer['approximate']
            answers.append(a)
        yaml_data['answers'] = answers
        return yaml_data
    
    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base+"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base+"[numerical_answer_type]"] = answer['numerical_answer_type']
            if answer['numerical_answer_type'] == 'exact_answer':
                result[base+"[answer_exact]"] = answer['exact']
                result[base+"[answer_error_margin]"] = answer['margin']
            elif answer['numerical_answer_type'] == 'range_answer':
                result[base+"[answer_range_start]"] = answer['start']
                result[base+"[answer_range_end]"] = answer['end']
            elif answer['numerical_answer_type'] == 'precision_answer':
                result[base+"[answer_precision]"] = answer['precision']
                result[base+"[answer_approximate]"] = answer['approximate']
        return result

class EssayQuestion(QuizQuestion):
    question_type = 'essay_question'

    def to_disk(self, force=False):
        return QuizQuestion.to_disk(self, force)
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        return yaml_data
    
    def to_json(self, course, resource_id):
        return QuizQuestion.to_json(self, course, resource_id)

class TextOnlyQuestion(QuizQuestion):
    question_type = 'text_only_question'

    def to_disk(self, force=False):
        return QuizQuestion.to_disk(self, force)
    
    @classmethod
    def _custom_from_disk(cls, yaml_data):
        return yaml_data
    
    def to_json(self, course, resource_id):
        return QuizQuestion.to_json(self, course, resource_id)
        
QUESTION_TYPES = {
    'fill_in_multiple_blanks_question': FillInMultipleBlanks,
    # TODO: Implement if someone ever asks
    #'calculated_question': FormulaQuestion,
    MatchingQuestions.question_type: MatchingQuestions,
    'short_answer_question': ShortAnswerQuestion,
    'multiple_choice_question': MultipleChoiceQuestion,
    'multiple_answers_question': MultipleAnswersQuestion,
    'true_false_question': TrueFalseQuestion,
    'multiple_dropdowns_question': MultipleDropDownsQuestion,
    'essay_question': EssayQuestion,
    'text_only_question': TextOnlyQuestion,
    'numerical_question': NumericalQuestion
}

class Quiz(Resource):
    category_names = ["quiz", "quizzes"]
    canvas_name = 'quizzes'
    canonical_category = 'quizzes'
    canvas_title_field = 'title'
    
    def to_disk(self, resource_id):
        '''Suitable YAML for yaml.dump'''
        result = CommentedMap()
        result['title'] = self.title
        result['url'] = self.html_url
        result['description'] = h2m(self.description)
        result['settings'] = CommentedMap()
        result['settings']['published'] = self.published
        result['settings']['quiz_type'] = self.quiz_type
        result['settings']['points_possible'] = self.points_possible
        result['settings']['allowed_attempts'] = self.allowed_attempts
        result['settings']['scoring_policy'] = self.scoring_policy
        result['settings']['timing'] = CommentedMap()
        result['settings']['timing']['due_at'] = self.due_at
        result['settings']['timing']['unlock_at'] = self.unlock_at
        result['settings']['timing']['lock_at'] = self.lock_at
        result['settings']['secrecy'] = CommentedMap()
        result['settings']['secrecy']['one_question_at_a_time'] = self.one_question_at_a_time
        result['settings']['secrecy']['shuffle_answers'] = self.shuffle_answers
        result['settings']['secrecy']['time_limit'] = self.time_limit
        result['settings']['secrecy']['cant_go_back'] = self.cant_go_back
        result['settings']['secrecy']['show_correct_answers'] = self.show_correct_answers
        result['settings']['secrecy']['show_correct_answers_last_attempt'] = self.show_correct_answers_last_attempt
        result['settings']['secrecy']['show_correct_answers_at'] = self.show_correct_answers_at
        result['settings']['secrecy']['hide_correct_answers_at'] = self.hide_correct_answers_at
        result['settings']['secrecy']['hide_results'] = self.hide_results
        result['settings']['secrecy']['one_time_results'] = self.one_time_results
        if self.access_code:
            result['settings']['secrecy']['access_code'] = self.access_code
        if self.ip_filter:
            result['settings']['secrecy']['ip_filter'] = self.ip_filter
        result['questions'] = [q.to_disk() for q in self.questions]
        return result
    
    @classmethod
    def extra_pull(cls, course, resource_id):
        quiz_id = resource_id.canvas_id
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, all=True)
        resource_id.canvas_data['questions'] = questions
    
    def extra_push(self, course, resource_id):
        quiz_id = resource_id.canvas_id
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, all=True)
        if 'errors' in questions:
            raise WaltzException("Errors in Canvas data: "+repr(questions))
        name_map = {q['question_name']: q['id'] for q in questions}
        for question in self.questions:
            json_data = question.to_json(course, resource_id)
            question.push(course, quiz_id, name_map, json_data)
        # Reorder elements as needed
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, all=True)
        name_map = {q['question_name']: q['id'] for q in questions}
        #payload = {}
        #for position, question in enumerate(self.questions):
        #    base = 'order[]'
        #    payload[base+'[id]'] = str(name_map[question.question_name])
        #    payload[base+'[type]'] = 'question'
        #pprint(payload)
        payload = {'order': []}
        for question in self.questions:
            payload['order'].append({
                'type': 'question',
                'id': str(name_map[question.question_name])
            })
        pprint(payload)
        print(post('quizzes/{}/reorder'.format(quiz_id), json=payload))
    
    def to_json(self, course, resource_id):
        ''' Suitable for PUT request on API'''
        return {
            'quiz[notify_of_update]': False,
            'quiz[title]': resource_id.canvas_title,
            'quiz[description]': self.description,
            'quiz[quiz_type]': self.quiz_type,
            'quiz[time_limit]': self.time_limit,
            'quiz[shuffle_answers]': self.shuffle_answers,
            'quiz[hide_results]': self.hide_results,
            'quiz[show_correct_answers]': self.show_correct_answers,
            'quiz[show_correct_answers_last_attempt]': self.show_correct_answers_last_attempt,
            'quiz[show_correct_answers_at]': self.show_correct_answers_at,
            'quiz[hide_correct_answers_at]': self.hide_correct_answers_at,
            'quiz[allowed_attempts]': self.allowed_attempts,
            'quiz[scoring_policy]': self.scoring_policy,
            'quiz[one_question_at_a_time]': self.one_question_at_a_time,
            'quiz[cant_go_back]': self.cant_go_back,
            'quiz[access_code]': self.access_code,
            'quiz[ip_filter]': self.ip_filter,
            'quiz[due_at]': self.due_at,
            'quiz[lock_at]': self.lock_at,
            'quiz[unlock_at]': self.unlock_at,
            'quiz[published]': self.published,
            'quiz[one_time_results]': self.one_time_results
        }
    
    @classmethod
    def from_disk(cls, course, yaml_data):
        # Fix configuration on simpler attributes
        yaml_data['description'] = m2h(yaml_data['description'])
        yaml_data['settings'].update(yaml_data['settings'].pop('timing'))
        yaml_data['settings'].update(yaml_data['settings'].pop('secrecy'))
        yaml_data.update(yaml_data.pop('settings'))
        yaml_data.setdefault('access_code', '')
        yaml_data.setdefault('ip_filter', '')
        yaml_data['html_url'] = yaml_data.pop('url')
        # Load in the questions
        questions = yaml_data.pop('questions')
        questions = [QuizQuestion.from_disk(course, question)
                     for question in questions]
        return cls(**yaml_data, questions=questions, course=course)
    
    @classmethod
    def from_json(cls, course, json_data):
        questions = get('quizzes/{qid}/questions'.format(qid=json_data['id']), 
                        course=course.course_name, all=True)
        questions = [QuizQuestion.from_json(course, question)
                     for question in questions]
        return cls(**json_data, questions=questions, course=course)

ALL_RESOURCES = [Quiz]
RESOURCE_CATEGORIES = {}
for ResourceType in ALL_RESOURCES:
    for category in ResourceType.category_names:
        RESOURCE_CATEGORIES[category] = ResourceType
