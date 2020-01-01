from waltz import defaults
from waltz.services.local import Local, LOCAL
from waltz.course import Course
from waltz.registry import Registry


def handle_registry(args, registry):
    if registry is None:
        return Registry.from_file(args.registry_path)
    return registry


def Add(args, registry=None):
    """
    Add a new course to the registry with the given name and location.

    Args:
        args:
        registry:

    Returns:

    """
    registry = handle_registry(args, registry)
    registry.add_course(args.name, args.path)
    if registry.default_course is None:
        registry.default_course = args.name
    registry.save_to_file()
    return registry


def Copy(args, registry=None):
    registry = handle_registry(args, registry)
    registry.copy_service(args.old, args)
    registry.save_to_file()
    return registry


def List(args, registry=None):
    registry = handle_registry(args, registry)
    if args.kind.lower() == 'courses':
        print("The following courses are available:")
        for course in registry.courses.values():
            print("\t", course.name)
    if args.kind.lower() == 'services':
        print("The following default services are available:")
        for service in defaults.get_default_services().values():
            print("\t", service.name, "(Default)")
        print("The following global services are available:")
        for service in registry.services.values():
            print("\t", service.name)
    return registry


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


def Download(args, registry=None):
    registry = handle_registry(args, registry)
    # Given service, go immediately find the resource
    # Otherwise we'll search for it the best we can
    # Ask everyone about who wants to search
    return registry


def Show(args, registry=None):
    registry = handle_registry(args, registry)