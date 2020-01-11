import logging
from waltz import defaults
from waltz.services.local import Local
from waltz.registry import Registry
from waltz.services.service import Service
from waltz.tools import extract_front_matter


def handle_registry(args, registry):
    if registry is None:
        return Registry.load(args.registry_path)
    return registry


def Init(args):
    if Registry.exists(args.directory):
        logging.warning("Existing Waltz registry in this directory.")
        if args.overwrite:
            Registry.delete(args.directory)
        else:
            return Registry.load(args.directory)
    registry = Registry.init(args.directory)
    registry.configure_service(Local(args.directory, {'path': args.directory}))
    registry.save_to_file()
    return registry


def Reset(args):
    registry = Registry.load(args.waltz_directory)
    registry.reset_database()
    registry.save_to_file()
    return registry


def Configure(args):
    registry = Registry.load(args.waltz_directory)
    new_service = Service.from_type(args.type).configure(args)
    registry.configure_service(new_service)
    registry.save_to_file()
    return registry


def List(args):
    registry = Registry.load(args.waltz_directory)
    if not args.service:
        print("The following services are available:")
        for service_type, services in registry.services.items():
            if services:
                print("\t", service_type+":")
                for service in services:
                    print("\t\t", service.name)
            else:
                print("\t", service_type + ":", "(none configured)")
    else:
        service = registry.get_service(args.service)
        service.list(registry, args)
    return registry


def Download(args):
    """
    > waltz download --filename for_loops.md
    > waltz download "Programming 37: For Loops"
    > waltz download assignment "Final Exam"
    > waltz download canvas "Final Exam"
    > waltz download canvas assignment "Final Exam"
    > waltz download canvas --id 234347437743

    > waltz download <Name>
    > waltz download <Service> <Name>
    > waltz download <Resource> <Name>
    > waltz download <Service> <Resource> <Name>
    > waltz download --parameter <Value>

    > waltz download --all

    """
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.download(registry, args)
    return registry


def Upload(args):
    """
    > waltz upload "Programming 37: For Loops"
        If service/category not in registry database,
        Then we can go ask all the services if they already know about
        this thing.
    """
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.upload(registry, args)


def Encode(args):
    """
    > waltz encode "Programming 37: For Loops"
    > waltz encode canvas assignment "Programming 37: For Loops"

    If we found out the resource category, we can include that in the Registry Database.
        That might also allow us to infer the Service.

    """
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.encode(registry, args)


def Push(args):
    registry = Registry.load(args.waltz_directory)
    resource_category = None
    if len(args.resource) == 1:
        local = registry.get_service('local', args.local_service)
        existing_file = local.find_existing(registry, args.resource[0], False, None)
        _, waltz, _ = extract_front_matter(local.read(existing_file))
        if 'resource' in waltz: # TODO: validate resource category
            resource_category = registry.get_resource_category(waltz['resource'])
            args.category = waltz['resource']
            args.title = args.resource[0]
            args.service = registry.get_service(resource_category.default_service).name
    if resource_category is None:
        resource_category = registry.guess_resource_category(args)
    resource_category.encode(registry, args)
    resource_category.upload(registry, args)


def Pull(args):
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.download(registry, args)
    resource_category.decode(registry, args)


def Decode(args):
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.decode(registry, args)


def Diff(args):
    registry = Registry.load(args.waltz_directory)
    resource_category = registry.guess_resource_category(args)
    resource_category.diff(registry, args)


def Search(args, registry=None):
    registry = handle_registry(args, registry)
    # Given service, go immediately find the resource
    # Otherwise we'll search for it the best we can
    # Ask everyone about who wants to search
    filter_by_services = []
    if args.service:
        filter_by_services.append(args.service)
    results = registry.search(args.category, args.what, filter_by_services)
    for result in results:
        print(result)
    return registry


def Show(args, registry=None):
    registry = handle_registry(args, registry)

