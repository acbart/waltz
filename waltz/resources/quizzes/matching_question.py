from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


class MatchingQuestion(QuizQuestion):
    question_type = 'matching_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.decode_question_common(registry, data, args)
        if args.hide_answers:
            result['answers'] = CommentedMap()
            result['answers']['lefts'] = list(sorted(set([answer['left'] for answer in data['answers']])))
            result['answers']['rights'] = (list(sorted(set([answer['right'] for answer in data['answers']])))
                                           +data['matching_answer_incorrect_matches'].split("\n"))
        else:
            result['answers'] = []
            for answer in data['answers']:
                a = CommentedMap()
                a['left'] = answer['left']
                a['right'] = answer['right']
                if answer.get('comments_html'):
                    a['comment'] = h2m(answer['comments_html'])
                result['answers'].append(a)
            result["distractors"] = data['matching_answer_incorrect_matches'].split("\n")
        return result

    # TODO: upload, encode

    def to_public(self, force=False):
        result = QuizQuestion.to_public(self, force)
        result['answers'] = CommentedMap()
        result['answers']['lefts'] = list(sorted(set([answer['left'] for answer in self.answers])))
        result['answers']['rights'] = list(sorted(set([answer['right'] for answer in self.answers])))
        return result

    @classmethod
    def _custom_from_disk(cls, yaml_data):
        yaml_data['matching_answer_incorrect_matches'] = yaml_data.pop('incorrect_matches', '')
        yaml_data['answers'] = [{'comments_html': m2h(answer.get('comment', '')),
                                 'left': answer['left'],
                                 'right': answer['right']}
                                for answer in yaml_data['answers']]
        return yaml_data

    def to_json(self, course, resource_id):
        result = QuizQuestion.to_json(self, course, resource_id)
        result['question[matching_answer_incorrect_matches]'] = self.matching_answer_incorrect_matches
        for index, answer in enumerate(self.answers):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_match_left]"] = answer['left']
            result[base + "[answer_match_right]"] = answer['right']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = 100  # TODO: Unnecessary?
            result[base + "[answer_precision]"] = 10  # TODO: Unnecessary?
        return result