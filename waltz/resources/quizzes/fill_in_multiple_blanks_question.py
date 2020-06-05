from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


class FillInMultipleBlanksQuestion(QuizQuestion):
    question_type = 'fill_in_multiple_blanks_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        if not args.hide_answers:
            result['answers'] = CommentedMap()
            for answer in data['answers']:
                blank_id = answer['blank_id']
                if blank_id not in result['answers']:
                    result['answers'][blank_id] = []
                a = CommentedMap()
                a['text'] = answer['text']
                if 'comments_html' in answer and answer['comments_html']:
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'][blank_id].append(a)
        return result

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        result['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['text'],
             'blank_id': blank_id}
            for blank_id, answers in data['answers'].items()
            for answer in answers
        ]
        return result

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        result = QuizQuestion._make_canvas_upload_common(registry, data, args)
        for index, answer in enumerate(data['answers']):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = 100
            result[base + "[blank_id]"] = answer['blank_id']
        return result
