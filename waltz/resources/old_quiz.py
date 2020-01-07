import os
from glob import glob

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import walk_tree

from waltz.tools.html_markdown_utilities import h2m, m2h

from waltz.tools.yaml_setup import yaml
from waltz.services.canvas.canvas_tools import get, put, post, delete

from waltz.tools.utilities import (to_friendly_date, from_friendly_date)
from waltz.resources import Resource, WaltzException



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
        result['settings']['timing']['due_at'] = to_friendly_date(self.due_at)
        result['settings']['timing']['unlock_at'] = to_friendly_date(self.unlock_at)
        result['settings']['timing']['lock_at'] = to_friendly_date(self.lock_at)
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
        result['groups'] = [g.to_disk() for g in self.groups]
        result['questions'] = [q.to_disk() for q in self.questions]
        return result
    
    def to_public(self, resource_id):
        result = CommentedMap()
        result['title'] = self.title
        result['description'] = h2m(self.description)
        result['settings'] = CommentedMap()
        result['settings']['quiz_type'] = self.quiz_type
        result['settings']['points_possible'] = self.points_possible
        result['settings']['allowed_attempts'] = self.allowed_attempts
        result['settings']['scoring_policy'] = self.scoring_policy
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
        result['groups'] = [g.to_public() for g in self.groups]
        result['questions'] = [q.to_public() for q in self.questions]
        return result
    
    @classmethod
    def extra_pull(cls, course, resource_id):
        if resource_id.canvas_data is True:
            return
        quiz_id = resource_id.canvas_id
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, retrieve_all=True)
        resource_id.canvas_data['questions'] = questions
        group_ids = {question['quiz_group_id'] for question in questions
                     if question['quiz_group_id'] is not None}
        groups = [get('quizzes/{qid}/groups/{gid}'.format(qid=quiz_id, gid=gid),
                      course=course.course_name)
                  for gid in group_ids]
        resource_id.canvas_data['groups'] = groups
    
    def extra_push(self, course, resource_id):
        quiz_id = resource_id.canvas_id
        # Get all the questions old information
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, retrieve_all=True)
        if 'errors' in questions:
            raise WaltzException("Errors in Canvas data: "+repr(questions))
        # Push all the groups
        group_ids = {question['quiz_group_id'] for question in questions
                     if question['quiz_group_id'] is not None}
        groups = [get('quizzes/{qid}/groups/{gid}'.format(qid=quiz_id, gid=gid),
                      course=course.course_name)
                  for gid in group_ids]
        group_map = {group['name']: group['id'] for group in groups}
        for group in self.groups:
            json_data = group.to_json(course, resource_id)
            group.push(course, quiz_id, json_data, group_map)
        # Push all the questions
        name_map = {q['question_name']: q['id'] for q in questions}
        for question in self.questions:
            if question.quiz_group_id is not None:
                question.quiz_group_id = group_map[question.quiz_group_id]
            json_data = question.to_json(course, resource_id)
            question.push(course, quiz_id, name_map, json_data)
            if question.question_name in name_map:
                del name_map[question.question_name]
        # Delete any old questions
        for leftover_name, leftover_id in name_map.items():
            deleted = delete('quizzes/{qid}/questions/{question_id}'.format(
                               qid=quiz_id, question_id=leftover_id),
                               course=course.course_name)
            print("Deleted", leftover_name, deleted)
        # Reorder questions as needed
        questions = get('quizzes/{qid}/questions/'.format(qid=quiz_id),
                        course=course.course_name, retrieve_all=True)
        return
        # TODO: Figure out how to get around the fact that Canvas doesn't
        #   allow you to download an ordering, so uploading an ordering is irrelevant.
        name_map = {q['question_name']: q['id'] for q in questions}
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
        yaml_data['due_at'] = from_friendly_date(yaml_data['due_at'])
        yaml_data['unlock_at'] = from_friendly_date(yaml_data['unlock_at'])
        yaml_data['lock_at'] = from_friendly_date(yaml_data['lock_at'])
        # Load in the questions
        groups = yaml_data.pop('groups')
        groups = [QuizGroup.from_disk(course, group, resource_id)
                  for group in groups]
        questions = yaml_data.pop('questions')
        questions = [QuizQuestion.from_disk(course, question, resource_id)
                     for question in questions]
        return cls(**yaml_data, questions=questions, groups=groups, course=course)
    
    @classmethod
    def from_json(cls, course, json_data):
        questions = get('quizzes/{qid}/questions'.format(qid=json_data['id']), 
                        course=course.course_name, retrieve_all=True)
        group_ids = {question['quiz_group_id'] for question in questions}
        groups = [QuizGroup.from_json(course,
                                      get('quizzes/{qid}/groups/{gid}'.format(qid=json_data['id'], gid=gid),
                                          course=course.course_name))
                  for gid in group_ids
                  if gid is not None]
        group_map = {group.id: group.name for group in groups}
        questions = [QuizQuestion.from_json(course, question, group_map)
                     for question in sorted(questions, key=sort_quiz_question)]
        return cls(**json_data, questions=questions, course=course, groups=groups)


def sort_quiz_question(q):
    if q['quiz_group_id']:
        return -q['quiz_group_id']
    else:
        return 0
