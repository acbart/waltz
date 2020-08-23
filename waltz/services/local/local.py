import os
from datetime import datetime

from natsort import natsorted
from tabulate import tabulate

from waltz.exceptions import WaltzException, WaltzAmbiguousResource
from waltz.resources.raw import RawResource
from waltz.services.service import Service
from waltz.tools import yaml, extract_front_matter
from waltz.tools.utilities import make_safe_filename, ensure_dir, make_end_path, all_path_parts_match


class Local(Service):
    """
    The local filesystem which can hold the Markdown version of files.

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
    the key "waltz". Or something? We should figure this out. That's just the ones that can be
    conveniently detected. The Local service can notice all Markdown files and manipulate them.

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
    type: str = "local"
    RESOURCES = {}

    def __init__(self, name: str, settings: dict):
        super().__init__(name, settings)
        self.path = settings['path']

    @classmethod
    def configure(cls, args):
        return cls(args.new, {'path': args.path})

    @classmethod
    def add_parser_configure(cls, parser):
        local_parser = parser.add_parser('local', help="Create another local filesystem to connect to.")
        local_parser.add_argument('new', type=str, help="A name to use to refer to the new local filesystem.")
        local_parser.add_argument('path', type=str, help="The path to the directory")
        return local_parser

    def list(self, registry, args):
        if args.category:
            category_names = registry.get_resource_category(args.category).category_names
        else:
            category_names = None
        rows = []
        for root, dirs, files in os.walk(self.path):
            for name in natsorted(files):
                if name.endswith(".md"):
                    path = os.path.join(root, name)
                    decoded_markdown = self.read(path)
                    try:
                        regular, waltz, body = extract_front_matter(decoded_markdown)
                    except:
                        if category_names is None:
                            rows.append(("[invalid]", "", os.path.relpath(path)))
                        continue
                    resource = "[{}]".format(waltz.get('resource', 'unknown'))
                    if category_names is None or waltz.get('resource') in category_names:
                        rows.append((resource, waltz.get("title", ""), os.path.relpath(path)))
        print(tabulate(rows, ("Resource", "Title", "Path")))

    @classmethod
    def add_parser_list(cls, parser, custom_name='local'):
        local_parser = parser.add_parser(custom_name, help="List all available recognized files.")
        local_parser.add_argument('category', type=str, nargs="?", help="An optional category to filter on.")
        local_parser.add_argument('--term', type=str, help="An optional search term")
        return local_parser

    def search(self, category, resource):
        return []

    @classmethod
    def make_markdown_filename(cls, filename, folder_file=None,
                               extension='.md'):
        start = make_safe_filename(filename)
        if folder_file is None:
            return start + extension
        return os.path.join(start, folder_file + extension)

    @classmethod
    def make_diff_filename(cls, filename):
        return make_safe_filename(filename) + ".diff.html"

    def find_existing(self, registry, title: str,
                      check_front_matter=False, top_directories=None,
                      folder_file=None, extension='.md', args=None):
        # Get the path to the file
        if hasattr(args, 'filename') and args.filename and os.path.exists(args.filename):
            safe_filename = args.filename
            args.title = self.get_title(args.filename)
        else:
            safe_filename = self.make_markdown_filename(title, extension=extension,
                                                        folder_file=folder_file)
        # Is the exact filepath here?
        if os.path.exists(safe_filename):
            return safe_filename
        # Ah, are we in the containing directory for the path?
        if os.path.exists(make_end_path(safe_filename)):
            return make_end_path(safe_filename)
        # Okay, search recursively from the .waltz file
        else:
            if top_directories is None:
                top_directories = [registry.search_up_for_waltz_registry('./')]
            potential_files = []
            for top_directory in top_directories:
                for root, dirs, files in os.walk(top_directory):
                    for file in files:
                        potential_file = os.path.join(root, file)
                        if all_path_parts_match(potential_file, safe_filename):
                            potential_files.append(potential_file)
                        elif check_front_matter and file.endswith(".md"):
                            _, waltz, _ = extract_front_matter(self.read(potential_file))
                            if waltz.get('title') == title:
                                potential_files.append(potential_file)
            if len(potential_files) > 1:
                raise WaltzAmbiguousResource("Ambiguous resource named {}:\n\t{}".format(
                    safe_filename, "\n\t".join(potential for potential in potential_files)
                ), potential_files)
            elif not potential_files:
                raise FileNotFoundError("No resource named {} found.".format(safe_filename))
            safe_filename, = potential_files
        return safe_filename

    def write(self, destination_path, body):
        ensure_dir(destination_path)
        with open(destination_path, 'w', encoding='utf8') as output_file:
            output_file.write(body)

    def read(self, source_path):
        with open(source_path, 'r', encoding='utf8') as input_file:
            return input_file.read()

    def get_title(self, filename):
        data = self.read(filename)
        regular, waltz, body = extract_front_matter(data)
        filename_as_title = os.path.splitext(os.path.basename(filename))[0]
        return waltz.get('title', filename_as_title)