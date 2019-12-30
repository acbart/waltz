"""
> waltz add course f19_cisc108 <LocalDirectory>
> waltz list services
  ...
  local
  canvas <Abstract>
  blockpy <Abstract>
  BlockPyGold <Global>
  ...
> waltz copy canvas UDCanvas <CanvasBaseUrl> <CanvasID> <CanvasToken> -l
> waltz copy local s19_local ../s19_cisc108/
> waltz list canvas resources Pages
   ...
   Policies- Syllabus
   Reference- String Methods
   Reference- Turtle Functions
   ...
> waltz pull "Reference- String Methods"
> waltz list local resources Pages
   ...
   Reference- String Methods
   ...
> waltz restyle f19_cisc108 "Reference- String Methods" html
... Modifies file to suit tastes
> waltz push f19_cisc108 "Reference- String Methods"
... Modifies web version
> waltz diff f19_cisc108 "Reference- String Methods"

"""
import argparse
import waltz.action as actions
from waltz import defaults


def parse_command_line(args):
    parser = argparse.ArgumentParser(prog='waltz', description='Sync resources between services for a course')
    parser.add_argument('--registry_path', type=str, help="Path to the registry file to use instead.",
                        default=defaults.REGISTRY_PATH)
    subparsers = parser.add_subparsers(help='Available commands')

    # Add Course
    parser_add = subparsers.add_parser('add', help='Add a new course')
    parser_add.add_argument('what', type=str, help="The name of the course you are adding. Choose "
                                                   "something convenient to type!")
    parser_add.add_argument('path', type=str, help="The local directory to associate with this course.")
    # TODO: allow path to be blank to reuse the name?
    parser_add.set_defaults(func=actions.Add)

    # Copy Service from course
    parser_copy = subparsers.add_parser('copy', help='Make a new copy of a service with modifications')
    parser_copy_services = parser_copy.add_subparsers(help="The name of the service you are copying.")
    for name, service in defaults.get_default_services().items():
        service.add_parser_copy(parser_copy_services)
    # TODO: allow path to be blank to reuse the name?
    parser_copy.set_defaults(func=actions.Copy)

    # List [Course|Service]
    parser_list = subparsers.add_parser('list', help='List available courses or services')
    parser_list.add_argument('kind', choices=["courses", "services"], type=str,
                             help="Either 'courses' or 'services'")
    # List services for current course
    # List all services
    # List all abstract services
    # List all generic services
    parser_list.set_defaults(func=actions.List)

    # Show [Course|Service]

    # Download

    # Upload

    # Restyle

    # Diff

    # Push

    # Pull

    # Extract

    # Build

    # Undo

    # ... Conclude!
    parsed = parser.parse_args(args)
    return parsed.func(parsed)

'''
parser.add_argument('verb', choices=['pull', 'push', 'build', 'publicize'])
parser.add_argument('--course', '-c', help='The specific course to perform operations on. Should be a valid course '
                                           'label, not the ID')
parser.add_argument('--settings', '-s', help='The settings file to use. Defaults to "settings.yaml". If the file does '
                                             'not exist, it will be created.', default='settings/settings.yaml')
parser.add_argument('--id', '-i', help='The specific resource ID to manipulate. If not specified, all resources are '
                                       'used', default=None)
parser.add_argument('--destination', '-d', help='Where course files will be downloaded to', default=None)
parser.add_argument('--format', '-f', help='What format to generate the result into.',
                    choices=['html', 'json', 'raw', 'pdf', 'text', 'yaml'], default='raw')
parser.add_argument('--ignore', '-x', help='Ignores any cached files in processing the quiz results',
                    action='store_true', default=False)
parser.add_argument('--quiet', '-q', help='Silences the output', action='store_true', default=False)
args = parser.parse_args()

waltz.sync.main(args)
'''