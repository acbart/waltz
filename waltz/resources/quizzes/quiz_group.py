from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.resources.quizzes import QuizQuestion


class QuizGroup(CanvasResource):
    category_name = ["quiz_group", "quiz_groups"]
    canonical_category = 'quiz_groups'

    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            setattr(self, key, value)
            del kwargs[key]

    @classmethod
    def decode_group(cls, group):
        result = CommentedMap()
        result['group'] = group['name']
        result['pick'] = group['pick_count']
        result['points'] = group['question_points']
        result['questions'] = []
        return result

    @classmethod
    def encode_group(cls, registry: Registry, data, args):
        return {
            'name': data['group'],
            'pick_count': data['pick'],
            'question_points': data['points']
        }

    @classmethod
    def encode_questions(cls, registry: Registry, data, args):
        questions = []
        for question in data['questions']:
            if isinstance(question, str):
                encoded = QuizQuestion.encode_question_by_title(registry, question, args)
            else:
                encoded = QuizQuestion.encode_question(registry, question, args)
            encoded['quiz_group_id'] = data['group']
            questions.append(encoded)
        return questions

    @classmethod
    def _make_canvas_upload(cls, registry: Registry, data, args):
        return {
            'quiz_groups[][name]': data['name'],
            'quiz_groups[][pick_count]': data['pick_count'],
            'quiz_groups[][question_points]': data['question_points']
        }

    @classmethod
    def from_json(cls, course, json_data):
        new_question = QuizGroup(course=course, **json_data)
        return new_question

    @classmethod
    def from_disk(cls, course, yaml_data, resource_id):
        yaml_data['pick_count'] = yaml_data.pop('pick')
        yaml_data['question_points'] = yaml_data.pop('points')
        return QuizGroup(course=course, **yaml_data)

    def push(self, course, quiz_id, json_data, group_map):
        '''
        Get all the questions in this quiz
        If this name is already in the quiz, then update it's compnents.
        Otherwise, create a new element.

        TODO: I think this is deprecated?
        '''
        if self.name in group_map:
            id = group_map[self.name]
            result = put("quizzes/{quiz}/groups/{group}/".format(
                quiz=quiz_id, group=id
            ), data=json_data, course=course.course_name)
        else:
            result = post("quizzes/{quiz}/groups/".format(
                quiz=quiz_id
            ), data=json_data, course=course.course_name)
            new_group = result["quiz_groups"][0]
            group_map[new_group['name']] = new_group['id']