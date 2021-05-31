from waltz.exceptions import WaltzException
from waltz.services.service import Service


class PEML(Service):
    type: str = "peml"
    RESOURCES = {}

    CONFIGURATION_SETTINGS = [
        ('url', True, "https://skynet.cs.vt.edu/peml-live/api/parse", 'The PEML remote service URL.')
    ]

    def __init__(self, name: str, settings: dict):
        super().__init__(name, settings)
        used_settings = {}
        for field, required, default_value, description in self.CONFIGURATION_SETTINGS:
            if field in settings and settings[field] is not None:
                used_settings[field] = settings[field]
            elif required:
                raise WaltzException("Missing required PEML configuration parameter {}".format(field))
            else:
                used_settings[field] = default_value


    @classmethod
    def configure(cls, args):
        return cls(args.new, {
            'url': args.url,
        })

    @classmethod
    def add_parser_configure(cls, parser):
        peml_parser = parser.add_parser('peml', help="Connect to PEML")
        peml_parser.add_argument('new', type=str, help="The new service that you will be creating.")
        for field, required, default_value, description in cls.CONFIGURATION_SETTINGS:
            peml_parser.add_argument('--'+field, help=description)
        return peml_parser
