import difflib
import json
import os
from typing import List

from waltz.registry import Registry
from waltz.services.service import Service
from waltz.tools.utilities import start_file, get_parent_directory


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
    folder_file = None

    DIFF_TEMPLATE = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
              "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html lang="en">
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <title></title>
            <style type="text/css">
                table.diff {{
                    font-family:Courier,serif;
                    border:medium;
                    margin-bottom: 4em;
                }}
                .diff_header {{background-color:#e0e0e0}}
                td.diff_header {{text-align:right}}
                .diff_next {{background-color:#c0c0c0}}
                .diff_add {{background-color:#aaffaa}}
                .diff_chg {{background-color:#ffff77}}
                .diff_sub {{background-color:#ffaaaa}}
            </style>
        </head>
        <body>
        {diffs}
        </body>
    </html>
    """

    @classmethod
    def diff(cls, registry: Registry, args):
        # Get local version
        local = registry.get_service(args.local_service, 'local')
        source_path = None
        try:
            source_path = local.find_existing(registry, args.title,
                                              folder_file=cls.folder_file, args=args)
        except FileNotFoundError:
            print("No local version of {}".format(args.title))
        # Get remote version
        service = registry.get_service(args.service, cls.default_service)
        service_name = service.type.title()
        resource_json = cls.find(service, args.title)
        if resource_json is None:
            print(f"No {service_name} version of {args.title}")
        # Do the diff if we can
        if not source_path or not resource_json:
            return False
        local_base = get_parent_directory(source_path)
        local_markdown = local.read(source_path)
        extra_local_files = cls.diff_extra_files(registry, local_markdown, args)
        remote_markdown, extra_remote_files = cls.decode_json(registry, json.dumps(resource_json), args)
        #extra_local_files, extra_remote_files = dict(extra_local_files), dict(extra_remote_files)
        extra_local_files={os.path.normpath(local_path): local_data
                            for local_path, local_data in dict(extra_local_files).items()}
        extra_remote_files = {os.path.normpath(remote_path): remote_data
                              for remote_path, remote_data in dict(extra_remote_files).items()}
        if args.console:
            # Handle main file
            for difference in difflib.ndiff(local_markdown.splitlines(True), remote_markdown.splitlines(True)):
                print(difference, end="")
            # Handle extra files
            for local_path, local_data in extra_local_files.items():
                if local_path in extra_remote_files:
                    print(local_path)
                    remote_data = extra_remote_files[local_path]
                    for difference in difflib.ndiff(local_data.splitlines(True), remote_data.splitlines(True)):
                        print(difference, end="")
                else:
                    print(f"No {service_name} version of {local_path}")
            for remote_path, remote_data in extra_remote_files.items():
                if remote_path not in extra_local_files:
                    print("No local version of", remote_path)
        else:
            html_differ = difflib.HtmlDiff(wrapcolumn=60)
            combined_diffs = [html_differ.make_table(local_markdown.splitlines(), remote_markdown.splitlines(),
                                                     fromdesc="Local: {}".format(source_path),
                                                     todesc=f"{service_name}: {args.title}")]
            # Handle extra files
            for local_path, local_data in extra_local_files.items():
                if local_path in extra_remote_files:
                    # File exists in remote and local
                    remote_data = extra_remote_files[local_path].splitlines()
                else:
                    # Local files that are not in the remote
                    remote_data = []
                combined_diffs.append("<strong>{}</strong>".format(local_path))
                combined_diffs.append(html_differ.make_table(local_data.splitlines(), remote_data,
                                                             fromdesc="Local",
                                                             todesc=service_name))
            for remote_path, remote_data in extra_remote_files.items():
                # Remote files that are not in the local
                if remote_path not in extra_local_files:
                    combined_diffs.append("<strong>{}</strong>".format(remote_path))
                    combined_diffs.append(html_differ.make_table([], remote_data.splitlines(),
                                                                 fromdesc="Local",
                                                                 todesc=service_name))
            local_diff_path = local.make_diff_filename(args.title)
            local_diff_path = os.path.join(os.path.dirname(source_path), local_diff_path)
            local.write(local_diff_path, cls.DIFF_TEMPLATE.format(diffs="\n\n".join(combined_diffs)))
            if not args.prevent_open:
                start_file(local_diff_path)

    @classmethod
    def decode_json(cls, registry: Registry, data, args):
        raise NotImplementedError(repr(data))

    @classmethod
    def encode_json(cls, registry: Registry, data, args):
        raise NotImplementedError(repr(data))

    @classmethod
    def find(cls, service: Service, data):
        raise NotImplementedError(repr(data))

    @classmethod
    def diff_extra_files(cls, registry: Registry, data, args):
        return []
