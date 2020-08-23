from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


class MultipleAnswersQuestion(QuizQuestion):
    question_type = 'multiple_answers_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        result['answers'] = []
        for answer in data['answers']:
            a = CommentedMap()
            html = h2m(cls._get_field(answer))
            if args.hide_answers:
                a['possible'] = html
            else:
                if answer['weight']:
                    a['correct'] = html
                else:
                    a['wrong'] = html
                if answer.get('comments_html'):
                    a['comment'] = h2m(answer['comments_html'])
            result['answers'].append(a)
        return result

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        text_mode = data['mode'] == 'text' if 'mode' in data else False
        result['answers'] = []
        for answer in data['answers']:
            result_answer = {'comments_html': m2h(answer.get('comment', "")),
                             'weight': 100 if 'correct' in answer else 0,
                             'text': answer['correct'] if 'correct' in answer else answer['wrong'],
                             'html': m2h(answer['correct'] if 'correct' in answer else answer['wrong'])}
            if text_mode:
                del result_answer['html']
            result['answers'].append(result_answer)
        return result

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        result = QuizQuestion._make_canvas_upload_common(registry, data, args)
        for index, answer in enumerate(data['answers']):
            base = 'question[answers][{index}]'.format(index=index)
            if 'html' in answer:
                result[base + "[answer_html]"] = answer['html']
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = answer['weight']
        return result
