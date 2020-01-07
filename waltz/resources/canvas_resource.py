import difflib
import json
import os

from waltz.registry import Registry
from waltz.resources.resource import Resource
from waltz.tools.utilities import start_file

class CanvasResource(Resource):
    name: str
    name_plural: str
    endpoint: str
    category_names: str
    id: str

    @classmethod
    def list(cls, canvas, args):
        resources = canvas.api.get(cls.endpoint, retrieve_all=True, data={"search_term": args.term})
        for resource in resources:
            print(resource['title'])

    @classmethod
    def find(cls, canvas, title):
        # TODO: Change canvas -> registry, title -> args
        resources = canvas.api.get(cls.endpoint, retrieve_all=True, data={"search_term": title})
        for resource in resources:
            if resource['title'] == title:
                full_quiz = canvas.api.get(cls.endpoint + str(resource[cls.id]))
                return json.dumps(full_quiz)
        return None

    @classmethod
    def download(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        resource_json = cls.find(canvas, args.title)
        if resource_json is not None:
            print("I found: ", args.title)
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
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=cls.name, disambiguate=args.url)
        try:
            destination_path = local.find_existing(registry, raw_resource.title)
        except FileNotFoundError:
            destination_path = local.make_markdown_filename(raw_resource.title)
            if args.destination:
                destination_path = os.path.join(args.destination, destination_path)
        decoded_markdown = cls.decode_json(registry, raw_resource.data, args)
        local.write(destination_path, decoded_markdown)

    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(decoded_markdown)
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
        remote_markdown = cls.decode_json(resource_json)
        if args.console:
            differences = difflib.ndiff(local_markdown.splitlines(True), remote_markdown.splitlines(True))
            for difference in differences:
                print(difference, end="")
        else:
            html_differ = difflib.HtmlDiff(wrapcolumn=60)
            html_diff = html_differ.make_file(local_markdown.splitlines(), remote_markdown.splitlines(),
                                              fromdesc="Local: {}".format(source_path),
                                              todesc="Canvas: {}".format(args.title))
            local_diff_path = local.make_diff_filename(args.title)
            local_diff_path = os.path.join(os.path.dirname(source_path), local_diff_path)
            local.write(local_diff_path, html_diff)
            if not args.prevent_open:
                start_file(local_diff_path)

    @classmethod
    def decode_json(cls, registry: Registry, data, args):
        raise NotImplemented()

    @classmethod
    def encode_json(cls, data):
        raise NotImplemented()

