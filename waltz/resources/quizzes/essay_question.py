from ruamel.yaml.comments import CommentedMap

from waltz.registry import Registry
from waltz.resources.quizzes.quiz_question import QuizQuestion
from waltz.tools import h2m


class EssayQuestion(QuizQuestion):
    question_type = 'essay_question'

    @classmethod
    def decode_json_raw(cls, registry: Registry, data, args):
        return QuizQuestion.decode_question_common(registry, data, args)

    @classmethod
    def encode_json_raw(cls, registry: Registry, data, args):
        return QuizQuestion.encode_question_common(registry, data, args)

    @classmethod
    def _make_canvas_upload_raw(cls, registry: Registry, data, args):
        return QuizQuestion._make_canvas_upload_common(registry, data, args)
