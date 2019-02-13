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

from waltz.html_markdown_utilities import h2m, m2h

from waltz.yaml_setup import yaml
from waltz.canvas_tools import get, put, post, delete

from waltz.utilities import (ensure_dir, make_safe_filename, indent4,
                             make_datetime_filename)
from waltz.resources import Resource

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
        if self.quiz_group_id:
            result['quiz_group_id'] = self.quiz_group_id
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
            'question[quiz_group_id]': self.quiz_group_id,
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
    def from_disk(cls, course, yaml_data, resource_id):
        question_type = yaml_data['question_type']
        actual_class = QUESTION_TYPES[question_type]
        yaml_data['question_text'] = m2h(yaml_data['question_text'])
        # Fix simplifications of comments
        for label in ['correct_comments', 'incorrect_comments', 'neutral_comments']:
            yaml_data[label+"_html"] = m2h(yaml_data.pop(label, ""))
        if 'quiz_group_id' not in yaml_data:
            yaml_data['quiz_group_id'] = None
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
            elif comment:
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
    extension = '.yaml'
    
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
        if resource_id.canvas_data is True:
            return
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
            if question.question_name in name_map:
                del name_map[question.question_name]
        for leftover_name, leftover_id in name_map.items():
            deleted = delete('quizzes/{qid}/questions/{question_id}'.format(
                               qid=quiz_id, question_id=leftover_id),
                               course=course.course_name)
            print("Deleted", leftover_name, deleted)
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
        print(post('quizzes/{}/reorder'.format(quiz_id), json=payload,
              course=course.course_name))
    
    def to_json(self, course, resource_id):
        ''' Suitable for PUT request on API'''
        return {
            'quiz[notify_of_update]': 'false',
            'quiz[title]': resource_id.canvas_title,
            'quiz[description]': self.description,
            'quiz[quiz_type]': self.quiz_type,
            'quiz[time_limit]': self.time_limit,
            'quiz[shuffle_answers]': str(self.shuffle_answers).lower(),
            'quiz[hide_results]': self.hide_results,
            'quiz[show_correct_answers]': str(self.show_correct_answers).lower(),
            'quiz[show_correct_answers_last_attempt]': str(self.show_correct_answers_last_attempt).lower(),
            'quiz[show_correct_answers_at]': self.show_correct_answers_at,
            'quiz[hide_correct_answers_at]': self.hide_correct_answers_at,
            'quiz[allowed_attempts]': self.allowed_attempts,
            'quiz[scoring_policy]': self.scoring_policy,
            'quiz[one_question_at_a_time]': str(self.one_question_at_a_time).lower(),
            'quiz[cant_go_back]': str(self.cant_go_back).lower(),
            'quiz[access_code]': self.access_code,
            'quiz[ip_filter]': self.ip_filter,
            'quiz[due_at]': self.due_at,
            'quiz[lock_at]': self.lock_at,
            'quiz[unlock_at]': self.unlock_at,
            'quiz[published]': str(self.published).lower(),
            'quiz[one_time_results]': str(self.one_time_results).lower()
        }
    
    @classmethod
    def from_disk(cls, course, yaml_data, resource_id):
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
        questions = [QuizQuestion.from_disk(course, question, resource_id)
                     for question in questions]
        return cls(**yaml_data, questions=questions, course=course)
    
    @classmethod
    def from_json(cls, course, json_data):
        questions = get('quizzes/{qid}/questions'.format(qid=json_data['id']), 
                        course=course.course_name, all=True)
        questions = [QuizQuestion.from_json(course, question)
                     for question in questions]
        return cls(**json_data, questions=questions, course=course)
