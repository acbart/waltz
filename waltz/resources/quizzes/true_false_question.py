from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


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

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        result['answers'] = [
            {'comments_html': m2h(data.get('if_true_chosen', "")),
             'weight': 100 if data['answer'] else 0,
             'text': 'True'},
            {'comments_html': m2h(data.get('if_false_chosen', "")),
             'weight': 100 if not data['answer'] else 0,
             'text': 'False'}]
        return result

    # TODO: upload

    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_text]"] = answer['text']
            result[base + "[answer_comment_html]"] = self._get_first_field(answer, 'comments_html', 'comments')
            result[base + "[answer_weight]"] = answer['weight']
        return result