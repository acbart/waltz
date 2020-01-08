from typing import List


class Resource:
    """
    A representation of some course material. Resources have various Actions that you can use
    to interact with them (upload, download, encode, decode, diff, etc.). A Resource is
    responsible for knowing what to do with those verbs when they are prompted.

    Resources can access any of the services. They have knowledge of all the command line
    arguments given, so that disambiguation can be given for their actions.

    The Resource Category is inferred by the Service from Action's arguments. Once dispatched,
    they might actually be using a different service to do their job, but the service has an
    important role in figuring out which resource category is involved.

    All Resources can a presence in the Registry Database. This is meant to be used as temporary
    storage between Actions, not a long-term database.

    Identifiers:
        The Title can be mapped to/fro a Filename, but that is lossy
        The local version has the Filename and Title.
        The remote version has the Title
        The ResourceCategory can also specify a disambiguation (id, url, something else)
    The actions always have a remote and local title that we are trying to match up
        Download
        Upload
        Encode
        Decode
        Diff
    """
    name: str
    id: str
    category_names: List[str]
    default_service: str


