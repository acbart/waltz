import difflib
import json
import os

from natsort import natsorted
from tabulate import tabulate
from tqdm import tqdm

from waltz.exceptions import WaltzException, WaltzAmbiguousResource
from waltz.registry import Registry
from waltz.resources.resource import Resource
from waltz.tools.utilities import start_file


class CanvasResource(Resource):
    name: str
    name_plural: str
    endpoint: str
    category_names: str
    id: str
    default_service = 'canvas'
    title_attribute: str = 'title'

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
    def sort_resource(cls, resource):
        for attribute in ['title', 'name', 'id']:
            try:
                return resource[attribute]
            except KeyError:
                pass
        return None

    @classmethod
    def list(cls, registry, canvas, args):
        local = registry.get_service(args.local_service, 'local')
        resources = canvas.api.get(cls.endpoint, retrieve_all=True, data={"search_term": args.term})
        rows = []
        for resource in natsorted(resources, key=cls.sort_resource):
            try:
                path = local.find_existing(registry, resource[cls.title_attribute])
                rows.append(("Yes", "Yes", resource[cls.title_attribute], os.path.relpath(path)))
            except WaltzAmbiguousResource as war:
                paths = "\n".join(os.path.relpath(path) for path in war.args[0])
                rows.append(("Yes", "Multiple", resource[cls.title_attribute], paths))
            except FileNotFoundError:
                rows.append(("Yes", "No", resource[cls.title_attribute], ""))
        print(tabulate(rows, ('Remote', 'Local', 'Title', 'Path')))


    @classmethod
    def find(cls, canvas, title):
        # TODO: Change canvas -> registry, title -> args
        resources = canvas.api.get(cls.endpoint, retrieve_all=True, data={"search_term": title})
        for resource in resources:
            if resource[cls.title_attribute] == title:
                return canvas.api.get(cls.endpoint + str(resource[cls.id]))
        return None

    @classmethod
    def download_all(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        local = registry.get_service('local')
        resources = canvas.api.get(cls.endpoint, retrieve_all=True)
        rows = []
        for resource in tqdm(natsorted(resources, key=cls.sort_resource)):
            try:
                path = local.find_existing(registry, resource[cls.title_attribute])
                rows.append(("Yes", "Yes", resource[cls.title_attribute], os.path.relpath(path)))
            except WaltzAmbiguousResource as war:
                paths = "\n".join(os.path.relpath(path) for path in war.args[0])
                rows.append(("Yes", "Multiple", resource[cls.title_attribute], paths))
            except FileNotFoundError:
                rows.append(("Yes", "No", resource[cls.title_attribute], ""))
            full_resource = canvas.api.get(cls.endpoint + str(resource[cls.id]))
            registry.store_resource(canvas.name, cls.name, resource[cls.title_attribute], "", json.dumps(full_resource))
        print(tabulate(rows, ('Remote', 'Local', 'Title', 'Path')))
        print("Downloaded", len(resources), cls.name_plural)

    @classmethod
    def download(cls, registry: Registry, args):
        if args.all:
            cls.download_all(registry, args)
            return
        canvas = registry.get_service(args.service, "canvas")
        resource_json = cls.find(canvas, args.title)
        if resource_json is not None:
            try:
                registry.find_resource(canvas.name, cls.name, args.title, "")
                print("Downloaded new version of {}: ".format(cls.name), args.title)
            except WaltzException:
                print("Downloaded new {}:".format(cls.name), args.title)
            resource_json = json.dumps(resource_json)
            registry.store_resource(canvas.name, cls.name, args.title, "", resource_json)
            return resource_json
        cls.find_similar(registry, canvas, args)

    @classmethod
    def find_similar(cls, registry: Registry, canvas, args):
        print("No", cls.name_plural, "with that title was found:", args.title)
        all_resources = canvas.api.get(cls.endpoint, retrieve_all=True)
        all_titles = [resource['title'] for resource in all_resources]
        similar_titles = difflib.get_close_matches(args.title, all_titles)
        if similar_titles:
            print("Similar", cls.name_plural, "found:")
            for title in similar_titles:
                print("\t", title)
        else:
            print("There were no similar", cls.name_plural, "found with that title.")

    @classmethod
    def decode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        # TODO: use disambiguate
        if args.all:
            raw_resources = registry.find_all_resources(service=args.service, category=cls.name)
        else:
            raw_resources = [registry.find_resource(title=args.title, service=args.service, category=cls.name)]
        for raw_resource in raw_resources:
            try:
                destination_path = local.find_existing(registry, raw_resource.title)
            except FileNotFoundError:
                destination_path = local.make_markdown_filename(raw_resource.title)
                if args.destination:
                    destination_path = os.path.join(args.destination, destination_path)
            decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
            local.write(destination_path, decoded_markdown)
            for path, data in extra_files:
                local.write(path, data)

    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(registry, decoded_markdown, args)
        registry.store_resource(args.service, cls.name, args.title, "", data)

    @classmethod
    def diff(cls, registry: Registry, args):
        # Get local version
        local = registry.get_service(args.local_service, 'local')
        source_path = None
        try:
            source_path = local.find_existing(registry, args.title)
        except FileNotFoundError:
            print("No local version of {}".format(args.title))
        # Get remote version
        canvas = registry.get_service(args.service, "canvas")
        resource_json = cls.find(canvas, args.title)
        if resource_json is None:
            print("No canvas version of {}".format(args.title))
        # Do the diff if we can
        if not source_path or not resource_json:
            return False
        local_markdown = local.read(source_path)
        extra_local_files = cls.diff_extra_files(registry, local_markdown, args)
        remote_markdown, extra_remote_files = cls.decode_json(registry, json.dumps(resource_json), args)
        extra_local_files, extra_remote_files = dict(extra_local_files), dict(extra_remote_files)
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
                    print("No canvas version of", local_path)
            for remote_path, remote_data in extra_remote_files.items():
                if remote_path not in extra_local_files:
                    print("No local version of", remote_path)
        else:
            html_differ = difflib.HtmlDiff(wrapcolumn=60)
            combined_diffs = [html_differ.make_table(local_markdown.splitlines(), remote_markdown.splitlines(),
                                                     fromdesc="Local: {}".format(source_path),
                                                     todesc="Canvas: {}".format(args.title))]
            # Handle extra files
            for local_path, local_data in extra_local_files.items():
                if local_path in extra_remote_files:
                    remote_data = extra_remote_files[local_path].splitlines()
                else:
                    remote_data = []
                combined_diffs.append("<strong>{}</strong>".format(local_path))
                combined_diffs.append(html_differ.make_table(local_data.splitlines(), remote_data,
                                                             fromdesc="Local",
                                                             todesc="Canvas"))
            for remote_path, remote_data in extra_remote_files.items():
                if remote_path not in extra_local_files:
                    combined_diffs.append("<strong>{}</strong>".format(remote_path))
                    combined_diffs.append(html_differ.make_table([], remote_data.splitlines(),
                                                                 fromdesc="Local",
                                                                 todesc="Canvas"))
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
    def diff_extra_files(cls, registry: Registry, data, args):
        return []
