from waltz import defaults
from waltz.services.local import Local, LOCAL
from waltz.course import Course
from waltz.registry import Registry


def handle_registry(args, registry):
    if registry is None:
        return Registry.from_file(args.registry_path)
    return registry


def Add(args, registry=None):
    registry = handle_registry(args, registry)
    registry.add_course(args.what, LOCAL.in_new_position(args.path))
    if registry.default_course is None:
        registry.default_course = args.what
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

def Show(args, registry=None):
    registry = handle_registry(args, registry)