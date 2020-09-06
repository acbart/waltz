from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


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
                if answer.get('comments_html'):
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'].append(a)
        return result

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        result['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['text']}
            for answer in data['answers']]
        return result

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        result = QuizQuestion._make_canvas_upload_common(registry, data, args)
        for index, answer in enumerate(data['answers']):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = 100
        return result
