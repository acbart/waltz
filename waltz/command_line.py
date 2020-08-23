"""
> waltz init
  Creates ".waltz" and ".waltz.db"
    "You are recommended to add these files to your .gitignore"
> waltz list services
  local
    ./
  canvas (no configurations)
  blockpy (no configurations)
> waltz configure canvas <CanvasBaseUrl> <CanvasID> <CanvasToken> -l
  local (./)
  canvas
    CourseCode: <CanvasBaseUrl>/courses/<CanvasID>
  blockpy
# Could configure multiple canvases, and then have to refer to them by name. But default can be "canvas".
> waltz list canvas Pages
   ...
   Policies- Syllabus
   Reference- String Methods
   Reference- Turtle Functions
   ...
> waltz pull canvas page "Reference- String Methods"
# Implicitly to this current folder, but could have specified. Didn't actually need `canvas` because its
#   the only configured service with that verb.
> waltz list local Pages
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
from waltz.registry import Registry


def parse_command_line(args):
    parser = argparse.ArgumentParser(prog='waltz', description='Sync resources between services for a course')
    parser.set_defaults(func=lambda args: parser.print_help())

    parser.add_argument('--waltz_directory', type=str, default="./",
                        help="Path to the main waltz directory with the Waltz registry and DB file.")
    subparsers = parser.add_subparsers(help='Available commands')

    # Init Waltz
    parser_init = subparsers.add_parser('init', help='Initialize a new Waltz here')
    parser_init.add_argument('--directory', "-d", type=str, default="./",
                             help="The local directory to use for this waltz; defaults to current directory.")
    parser_init.add_argument('--overwrite', "-o", action="store_true", default=False,
                             help="If used, then overwrites the existing waltz registry.")
    parser_init.set_defaults(func=actions.Init)


    # Reset Database
    parser_reset = subparsers.add_parser('reset', help='Reset the Waltz database entirely.')
    parser_reset.set_defaults(func=actions.Reset)


    # Configure service
    parser_configure = subparsers.add_parser('configure', help='Configure a new instance of the service.')
    parser_configure_services = parser_configure.add_subparsers(dest='type',
                                                                help="The type of the service you are configuring.")
    for name, service_type in defaults.get_service_types().items():
        service_type.add_parser_configure(parser_configure_services)
    parser_configure.set_defaults(func=actions.Configure)

    # List Services or Resources
    parser_list = subparsers.add_parser('list', help='List available services or resources')
    parser_list_services = parser_list.add_subparsers(dest='service', help="The service to search within.")
    for name, service_type in defaults.get_service_types().items():
        service_type.add_parser_list(parser_list_services)
    registry = Registry.load('./', False)
    if registry is not None:
        for name, services in registry.services.items():
            for service_type in services:
                service_type.add_parser_list(parser_list_services, service_type.name)
        # TODO: Make this close more elegant
        #   It's absolutely needed though, otherwise the DB stays open!
        registry.db.close()
    parser_list.set_defaults(func=actions.List)

    # Show [Course|Service]

    # Search
    parser_search = subparsers.add_parser('search', help='Search for a resource.')
    parser_search.add_argument('category', type=str, help="The category of resource to search")
    parser_search.add_argument('what', type=str, help="The resource to download")
    parser_search.add_argument("--service", type=str, help="The specific service to use in case of ambiguity.")
    parser_search.set_defaults(func=actions.Search)

    def add_id_and_url(subparser):
        subparser.add_argument("--id", help="A resource-specific ID to disambiguate this resource definitively.")
        subparser.add_argument("--url", help="A resource-specific URL to disambiguate this resource definitively.")
        subparser.add_argument("--filename", help="A resource-specific local Filename to disambiguate this resource definitively.")
        subparser.add_argument("--all", action='store_true', help="Get all the resources of this type.")

    # Download
    parser_download = subparsers.add_parser('download', help='Download the raw version of a resource.')
    parser_download.add_argument('resource', nargs='+', type=str, help="The resource to download. Could be a "
                                 "resource title, filename, or some combination of those and the service and category.")
    add_id_and_url(parser_download)
    parser_download.set_defaults(func=actions.Download)

    # Upload
    parser_upload = subparsers.add_parser('upload', help='Upload the raw version of a resource.')
    parser_upload.add_argument('resource', nargs='+', type=str, help="The resource to download. Could be a "
                                                                       "resource title, filename, or some combination of those and the service and category.")
    add_id_and_url(parser_upload)
    parser_upload.set_defaults(func=actions.Upload)

    # Decode
    parser_decode = subparsers.add_parser('decode', help='Convert a raw resource into a locally editable one.')
    parser_decode.add_argument('resource', nargs='+', type=str, help="The resource to decode. Could be a "
                               "filename, resource title, or some combination of those and the service and category.")
    parser_decode.add_argument("--local_service", type=str, help="The specific local service to use as an override.")
    parser_decode.add_argument("--destination", "-d", type=str, help="The destination directory for this resource.")
    parser_decode.add_argument("--combine", "-c", action='store_true', default=False,
                               help="Whether to combine all subresources into a single file.")
    parser_decode.add_argument("--hide_answers", action='store_true', default=False,
                               help="Whether to hide answers to any questions.")
    parser_decode.add_argument("--banks", nargs="*", type=str,
                               help="The question bank folders to check. First one will be the location for new questions.")
    add_id_and_url(parser_decode)
    # TODO: Allow override of specific local, but otherwise assume default `local`?
    parser_decode.set_defaults(func=actions.Decode)

    # Encode
    parser_encode = subparsers.add_parser('encode', help='Convert a locally editable resource into a raw one.')
    parser_encode.add_argument('resource', nargs='+', type=str, help="The resource to encode. Could be a "
                               "filename, resource title, or some combination of those and the service and category.")
    parser_encode.add_argument("--local_service", type=str, help="The specific local service to use as an override.")
    parser_encode.add_argument("--banks", nargs="*", type=str,
                               help="The question bank folders to check.")
    add_id_and_url(parser_encode)
    parser_encode.set_defaults(func=actions.Encode)

    # Diff
    parser_diff = subparsers.add_parser('diff', help='Compare the remote version of a resource and the local one.')
    parser_diff.add_argument('resource', nargs='+', type=str, help="The resource to diff. Could be a "
                             "filename, resource title, or some combination of those and the service and category.")
    parser_diff.add_argument("--local_service", type=str, help="The specific local service to use as an override.")
    parser_diff.add_argument("--console", action="store_true",
                             help="Do not generate HTML file; just print to console.")
    parser_diff.add_argument("--prevent_open", action="store_true",
                             help="Prevent the generated HTML file from being automatically opened in your browser.")
    parser_diff.add_argument("--banks", nargs="*", type=str,
                             help="The question bank folders to check.")
    parser_diff.add_argument("--combine", "-c", action='store_true', default=False,
                             help="Whether to combine all subresources into a single file.")
    parser_diff.add_argument("--hide_answers", action='store_true', default=False,
                             help="Whether to hide answers to any questions.")
    parser_diff.add_argument("--destination", "-d", type=str, help="The destination directory for this resource.")
    add_id_and_url(parser_diff)
    parser_diff.set_defaults(func=actions.Diff)

    # Push
    parser_push = subparsers.add_parser('push', help='Convert a locally editable resource into a raw one and upload it.')
    parser_push.add_argument('resource', nargs='+', type=str, help="The resource to encode and upload. Could be a "
                                                                     "filename, resource title, or some combination of those and the service and category.")
    parser_push.add_argument("--local_service", type=str, help="The specific local service to use as an override.")
    parser_push.add_argument("--banks", nargs="*", type=str,
                               help="The question bank folders to check.")
    add_id_and_url(parser_push)
    parser_push.set_defaults(func=actions.Push)

    # Pull
    parser_pull = subparsers.add_parser('pull',
                                        help='Download a raw resource and convert it to a locally editable one.')
    parser_pull.add_argument('resource', nargs='+', type=str, help="The resource to download and decode. Could be a "
                                                                   "filename, resource title, or some combination of those and the service and category.")
    parser_pull.add_argument("--local_service", type=str, help="The specific local service to use as an override.")
    parser_pull.add_argument("--banks", nargs="*", type=str,
                             help="The question bank folders to check.")
    parser_pull.add_argument("--combine", "-c", action='store_true', default=False,
                             help="Whether to combine all subresources into a single file.")
    parser_pull.add_argument("--hide_answers", action='store_true', default=False,
                             help="Whether to hide answers to any questions.")
    parser_pull.add_argument("--destination", "-d", type=str, help="The destination directory for this resource.")
    add_id_and_url(parser_pull)
    parser_pull.set_defaults(func=actions.Pull)

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