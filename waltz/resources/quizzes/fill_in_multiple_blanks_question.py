from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


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
                if answer['comments_html']:
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'][blank_id].append(a)
        return result

    # TODO: upload, encode

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
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[answer_weight]"] = 100
            result[base + "[blank_id]"] = answer['blank_id']
        return result