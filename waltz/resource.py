from typing import List

class Style:
    pass


class Difference:
    pass


class Category:
    name: str
    id: str


class Resource:
    name: str
    id: str
    category: Category
    styles: List[Style]

    def restyle(self, new_style):
        pass

    def diff(self, other) -> List[Difference]:
        pass


class CanvasQuiz(Resource):
    """

    """
    pass
