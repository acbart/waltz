import difflib
import json
import os
import sys
from pprint import pprint

from ruamel.yaml.comments import CommentedMap

from waltz.exceptions import WaltzAmbiguousResource, WaltzResourceNotFound
from waltz.registry import Registry
from waltz.resources.canvas_resource import CanvasResource
from waltz.tools import h2m, extract_front_matter
from waltz.resources.raw import RawResource
from waltz.resources.resource import Resource
from waltz.tools.html_markdown_utilities import hide_data_in_html, m2h, add_to_front_matter
from waltz.tools.utilities import get_files_last_update, from_canvas_date, to_friendly_date_from_datetime, start_file, \
    blockpy_string_to_datetime, from_friendly_date

class BlockPyResource(Resource):
    default_service = 'blockpy'

    @classmethod
    def decode(cls, registry: Registry, args):
        local = registry.get_service(args.local_service, 'local')
        # TODO: use disambiguate
        if args.all:
            raw_resources = registry.find_all_resources(service=args.service, category=cls.name)
        else:
            raw_resources = [registry.find_resource(title=args.title,
                                                    service=args.service, category=cls.name)]
        folder = None if args.combine else cls.folder_file
        for raw_resource in raw_resources:
            destination_path = local.find_or_new(registry, raw_resource, folder, args)
            decoded_markdown, extra_files = cls.decode_json(registry, raw_resource.data, args)
            local.write(destination_path, decoded_markdown)
            for path, data in extra_files:
                local.write(path, data)

    @classmethod
    def encode(cls, registry: Registry, args):
        folder = None if args.combine else cls.folder_file
        local = registry.get_service(args.local_service, 'local')
        source_path = local.find_existing(registry, args.title, folder_file=folder)
        decoded_markdown = local.read(source_path)
        data = cls.encode_json(registry, decoded_markdown, args)
        registry.store_resource(args.service, cls.name, args.title, "", data)