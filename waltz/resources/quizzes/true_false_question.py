from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


class TrueFalseQuestion(QuizQuestion):
    question_type = 'true_false_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        if not args.hide_answers:
            comments = CommentedMap()
            for answer in data['answers']:
                if answer['text'] == 'True':
                    result['answer'] = True if answer['weight'] else False
                    if answer['comments_html']:
                        comments['if_true_chosen'] = h2m(answer['comments_html'])
                elif answer['comments_html']:
                    comments['if_false_chosen'] = h2m(answer['comments_html'])
            if comments and any(comments.values()):
                result['comments'] = comments
        return result

    # TODO: upload, encode

    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['answers'] = [
            {'comments_html': m2h(yaml_data.get('true_comment', "")),
             'weight': 100 if yaml_data['answer'] else 0,
             'text': 'True'},
            {'comments_html': m2h(yaml_data.get('false_comment', "")),
             'weight': 100 if not yaml_data['answer'] else 0,
             'text': 'False'}]
        return yaml_data

    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[answer_weight]"] = answer['weight']
        return result