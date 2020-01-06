import difflib
import json
import os
import sys

from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file


class Page(CanvasResource):
    """
    DOWNLOAD: gets a copy of the raw JSON version of this from Canvas
    PULL: DOWNLOAD as JSON, then RESTYLE into Markdown
    PUSH: RESTYLE from Markdown into JSON, then UPLOAD
    UPLOAD: sends the copy of the raw JSON version of this into Canvas
    EXTRACT: RESTYLE from HTML to YAML using a template
    BUILD: RESTYLE from YAML to HTML using a template
    """
    name = "page"
    category_names = ['page', 'pages']

    @classmethod
    def list(cls, canvas, args):
        pages = canvas.api.get("pages/", retrieve_all=True, data={"search_term": args.term})
        for page in pages:
            print(page['title'])

    @classmethod
    def find(cls, canvas, title):
        pages = canvas.api.get("pages/", retrieve_all=True, data={"search_term": title})
        for page in pages:
            if page['title'] == title:
                full_page = canvas.api.get("pages/{}".format(page['url']))
                return json.dumps(full_page)
        return None

    @classmethod
    def download(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        page_json = cls.find(canvas, args.title)
        if page_json is not None:
            print("I found: ", args.title)
            registry.store_resource(canvas.name, cls.name, args.title, "", page_json)
            return page_json
        print("No resource with that title was found:", args.title)
        all_pages = canvas.api.get("pages/", retrieve_all=True)
        all_titles = [page['title'] for page in all_pages]
        similar_titles = difflib.get_close_matches(args.title, all_titles)
        if similar_titles:
            print("Similar pages found:")
            for title in similar_titles:
                print("\t", title)
        else:
            print("There were no similar pages found with that title.")

    @classmethod
    def upload(cls, registry: Registry, args):
        canvas = registry.get_service(args.service, "canvas")
        raw_resource = registry.find_resource(title=args.title, service=args.service,
                                              category=args.category, disambiguate=args.url)
        full_page = json.loads(raw_resource.data)
        canvas.api.put("pages/{url}".format(url=full_page['title']), data={
            'wiki_page[title]': full_page['title'],
            'wiki_page[body]': full_page['body'],
            'wiki_page[published]': full_page['published']
        })
        # TODO: Handle other fields
        # wiki_page[editing_roles]
        # wiki_page[notify_of_update]
        # wiki_page[front_page]

    @classmethod
    def add_parser_download(cls, parser):
        canvas_parser = parser.add_parser('page', help="Download the given page.")
        canvas_parser.add_argument('title', type=str, help="The title or ID of the page.")
        return canvas_parser

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
        decoded_markdown = cls.decode_json(raw_resource.data)
        local.write(destination_path, decoded_markdown)

    @classmethod
    def decode_json(cls, data: str):
        raw_data = json.loads(data)
        return h2m(raw_data['body'], {
            'title': raw_data['title'],
            'resource': 'Page',
            'published': raw_data['published']
        })

    @classmethod
    def encode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(decoded_markdown)
        registry.store_resource(args.service, cls.name, args.title, "", data)

    @classmethod
    def encode_json(cls, decoded_markdown):
        regular, waltz, body = extract_front_matter(decoded_markdown)
        body = hide_data_in_html(regular, m2h(body))
        return json.dumps({
            'title': waltz['title'],
            'published': waltz['published'],
            'body': body
            # TODO: Other fields
        })

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
        page_json = cls.find(canvas, args.title)
        if page_json is None:
            print("No canvas version of {}".format(args.title))
        # Do the diff if we can
        if not source_path or not page_json:
            return False
        local_markdown = local.read(source_path)
        remote_markdown = cls.decode_json(page_json)
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