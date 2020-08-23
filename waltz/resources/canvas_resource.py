import difflib
import json
import os

from natsort import natsorted
from tabulate import tabulate
from tqdm import tqdm

from waltz.exceptions import WaltzException, WaltzAmbiguousResource
from waltz.registry import Registry
from waltz.resources.resource import Resource


class CanvasResource(Resource):
    name: str
    name_plural: str
    endpoint: str
    category_names: str
    id: str
    default_service = 'canvas'
    title_attribute: str = 'title'

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
                path = local.find_existing(registry, resource[cls.title_attribute], args=args)
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
                path = local.find_existing(registry, resource[cls.title_attribute], args=args)
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
                destination_path = local.find_existing(registry, raw_resource.title, args=args, folder_file=cls.folder_file)
            except FileNotFoundError:
                destination_path = local.make_markdown_filename(raw_resource.title, folder_file=cls.folder_file)
                if args.destination:
                    destination_path = os.path.join(args.destination, destination_path)
            decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
            local.write(destination_path, decoded_markdown)
            for path, data in extra_files:
                local.write(path, data)

    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title, args=args, folder_file=cls.folder_file)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(registry, decoded_markdown, args)
        registry.store_resource(args.service, cls.name, args.title, "", data)


