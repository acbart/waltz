from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


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
                if answer['comments_html']:
                    a['comment'] = h2m(answer['comments_html'])
            result['answers'][blank_id].append(a)
        return result

    # TODO: upload, encode

    def to_public(self, force=False):
        result = QuizQuestion.to_public(self, force)
        result['answers'] = CommentedMap()
        for answer in self.answers:
            blank_id = answer['blank_id']
            if blank_id not in result['answers']:
                result['answers'][blank_id] = []
            result['answers'][blank_id].append(answer['text'])
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
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[answer_weight]"] = answer['weight']
            result[base + "[blank_id]"] = answer['blank_id']
        return result