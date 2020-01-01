from typing import List


class Style:
    pass


class Difference:
    pass


class Resource:
    """
    A representation of some course material. Every Resource is associated with the Local service
    so that it can be represented on disk. It will also be strongly associated with some other service
    that can place it remotely.

    Resources can be restyled, but are fundamentally represented by some canonical style.
    """
    name: str
    id: str
    category_names: List[str]
    styles: List[Style]

    def restyle(self, new_style):
        pass

    def diff(self, other) -> List[Difference]:
        pass

