from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m, m2h


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
            if data.get('matching_answer_incorrect_matches'):
                result["distractors"] = data['matching_answer_incorrect_matches'].split("\n")
        return result

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        result = QuizQuestion.encode_question_common(registry, data, args)
        result['matching_answer_incorrect_matches'] = "\n".join(data.get('distractors', []))
        result['answers'] = [{'comments_html': m2h(answer.get('comment', '')),
                              'left': answer['left'],
                              'right': answer['right']}
                             for answer in data['answers']]
        return result

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        result = QuizQuestion._make_canvas_upload_common(registry, data, args)
        result['question[matching_answer_incorrect_matches]'] = data['matching_answer_incorrect_matches']
        for index, answer in enumerate(data['answers']):
            base = 'question[answers][{index}]'.format(index=index)
            result[base + "[answer_match_left]"] = answer['left']
            result[base + "[answer_match_right]"] = answer['right']
            result[base + "[answer_comment_html]"] = answer['comments_html']
            result[base + "[answer_weight]"] = 100  # TODO: Unnecessary?
            result[base + "[answer_precision]"] = 10  # TODO: Unnecessary?
        return result