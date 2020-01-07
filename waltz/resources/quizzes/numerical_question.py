from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


class NumericalQuestion(QuizQuestion):
    question_type = 'numerical_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        if not args.hide_answers:
            result['answers'] = []
            for answer in data['answers']:
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
                if answer.get('comments_html'):
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'].append(a)
        return result

    # TODO: upload, encode

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
                a['margin'] = answer.get('margin', 0)
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
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[numerical_answer_type]"] = answer['numerical_answer_type']
            if answer['numerical_answer_type'] == 'exact_answer':
                result[base + "[answer_exact]"] = answer['exact']
                result[base + "[answer_error_margin]"] = answer.get('margin', 0)
            elif answer['numerical_answer_type'] == 'range_answer':
                result[base + "[answer_range_start]"] = answer['start']
                result[base + "[answer_range_end]"] = answer['end']
            elif answer['numerical_answer_type'] == 'precision_answer':
                result[base + "[answer_precision]"] = answer['precision']
                result[base + "[answer_approximate]"] = answer['approximate']
        return result