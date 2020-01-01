from waltz import defaults
from waltz.services.service import Service


class Local(Service):
    """
    The local filesystem, which can hold a lot of resources in different styles.

    The filesystem layout shall not be strict. Instructors are free to organize however
    they see fit, and the system has to deal with it. If the instructors choose to buy
    in, then they get the added advantage of being able to relayout their directory
    automatically. Reorganize function - can regroup resources by category or by time.

    Index Database - a sqlite database that is used to hold temporary versions of files.
    This should not be committed to your database. Or maybe this should be compressed files
    on the hard drive so that they can be committed? No, because that makes merges from separate
    branches too intractable. If you want version control of a file, then its up to you to talk
    to your VCS about it - we are not responsible for version controlling your file. This is just
    a mechanism for helping us manage data.

    To be "Waltz-Aware", a Resource file needs to be markdown (required?) that has front-matter with
    the key "waltz". Or something? We should figure this out.

    Fundamentally, what is a Resource to the Local Service? Let's take a bunch of examples and styles.

    Canvas Page
        Raw JSON format | Friendly Markdown Format | Previewable Web Format
    Canvas Assignment
        Raw JSON format | Friendly Markdown Format | Previewable Web Format
    Canvas File/Filesystem
        You can have a stand-alone file that you push/pull by filename
        You can have a special file that sits next to the file and acts as info, has to travel with it
        You can have a folder with a special index file that lets you sync a directory
    Canvas Quiz
        Raw JSON format | Single file Yaml | Multi file Markdown | Previewable Web Format
        In multi-file format, 
    Canvas Quiz Question, Canvas Quiz Group
        Could be its own separate markdown file
    Canvas Modules Layout
        Raw JSON format | Friendly Markdown Format | Previewable Web Format
    BlockPy Assignment
        Raw JSON
        Friendly Editable Format
            Markdown file for instructions
                Yaml frontmatter for settings
            Python files:
                starting_code.py
                on_run.py
                on_change.py
                url_data.yaml
                _instructor_files/
                _starting_files/
                _student_files/
                _sample_submissions/

    BlockPy Group/Membership
        JSON file with references to the specific IDs or files?
        Folder with special index file inside?
    YouTube Video
        Video file | Video settings file
    *Learning Objective
    *Misconception

    Let's talk about how people want to identify resources.
        Filename, full path to file
        Title of resource
        Partial title of resource
        Unique ID + category

    Let's explore some scenarios:
        Programming problem sets:
            I download "Programming 25) Unit Tests", a Canvas Assignment
            I also grab "Programming 25) Unit Tests", a BlockPy Group

        Final Project:
            I download "Final Project" a Canvas Assignment
                Final Project.md
            I download "Final Project" a BlockPy Assignment
                Final Project.md
            I download "Final Project" a Canvas Page
                Final Project.md

        In theory, Canvas is perfectly happy to have 10 assignments all named "Banana"
            I suppose we need a fully qualified name to resolve ambiguities
            Title_Service_Category_Id.md
            It'll try to pick the shortest possible name that is unambigious, preferring
            these components: Title, Category, Service, Id
    """
    name: str
    parent_name : str

    @classmethod
    def in_new_position(cls, path):
        return Local('local', 'local', {'path': path}, False)

    def copy(self, updates):
        return Local(updates.name, 'local', {'path': updates.path}, False)

    def add_parser_copy(self, parser):
        local_parser = parser.add_parser('local', help="Create another local filesystem to connect to.")
        local_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        local_parser.add_argument('path', type=str, help="The path to the directory")
        return local_parser

    def search(self, category, resource):
        return []

LOCAL = Local('local', None, {'path': None}, True)

defaults.register_default_service(LOCAL)