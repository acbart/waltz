from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


class MultipleChoiceQuestion(QuizQuestion):
    question_type = 'multiple_choice_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        result['answers'] = []
        for answer in data['answers']:
            a = CommentedMap()
            html = h2m(answer['html'])
            if args.hide_answers:
                a['possible'] = html
            else:
                if answer['weight']:
                    a['correct'] = html
                else:
                    a['wrong'] = html
                if answer['comments_html']:
                    a['comment'] = h2m(answer['comments_html'])
            result['answers'].append(a)
        return result

    # TODO: upload, encode

    @classmethod
    def _custom_from_disk(cls, yaml_data):
        print(yaml_data['question_name'])
        yaml_data['answers'] = [
            {'comments_html': m2h(answer.get('comment', "")),
             'weight': 100 if 'correct' in answer else 0,
             'html': m2h(answer['correct'] if 'correct' in answer
                         else answer['wrong'])}
            for answer in yaml_data['answers']]
        return yaml_data

    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base +"[answer_html]"] = self._get_first_field(answer, 'html', 'text')
            result[base +"[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base +"[answer_weight]"] = answer['weight']
        return result