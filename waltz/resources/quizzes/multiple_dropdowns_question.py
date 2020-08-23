from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


class MultipleDropDownsQuestion(QuizQuestion):
    question_type = 'multiple_dropdowns_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        result['answers'] = CommentedMap()
        for answer in data['answers']:
            blank_id = answer['blank_id']
            if blank_id not in result['answers']:
                result['answers'][blank_id] = []
            a = CommentedMap()
            text = answer['text']
            if args.hide_answers:
                a['possible'] = text
            else:
                if answer['weight']:
                    a['correct'] = text
                else:
                    a['wrong'] = text
                if answer.get('comments_html'):
                    a['comment'] = h2m(answer['comments_html'])
            result['answers'][blank_id].append(a)
        return result

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        result['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'text': answer['correct'] if 'correct' in answer
             else answer['wrong'],
             'weight': 100 if 'correct' in answer else 0,
             'blank_id': blank_id}
            for blank_id, answers in data['answers'].items()
            for answer in answers]
        return result

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        result = QuizQuestion._make_canvas_upload_common(registry, data, args)
        for index, answer in enumerate(data['answers']):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = answer['weight']
            result[base + "[blank_id]"] = answer['blank_id']
        return result
