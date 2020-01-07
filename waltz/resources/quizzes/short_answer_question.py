from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m



class ShortAnswerQuestion(QuizQuestion):
    question_type = 'short_answer_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        if not args.hide_answers:
            result['answers'] = []
            for answer in data['answers']:
                a = CommentedMap()
                a['text'] = answer['text']
                if answer['comments_html']:
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'].append(a)
        return result

    # TODO: upload, encode

    def to_public(self, force=False):
        return QuizQuestion.to_public(self, force)

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
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[answer_weight]"] = 100
        return result