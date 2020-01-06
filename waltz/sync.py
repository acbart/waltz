import os
import requests_cache

try:
    from tqdm import tqdm
except:
    print("TQDM is not installed. No progress bars will be available.")
    tqdm = list

from glob import glob

from waltz.tools.yaml_setup import yaml

from waltz.services.canvas.canvas_tools import get_setting, get_courses
from waltz.services.canvas.canvas_tools import load_settings
from waltz.tools.utilities import global_settings, log
from waltz.resources import (ResourceID, WaltzException,
                             Course, Page)


def pull_all_resources(resource_ids, format, destination, course_name, ignore):
    course = Course(destination, course_name)
    category, _, _, resource_type = ResourceID._parse_type(resource_ids)
    resource_list = resource_type.find_resource_on_canvas(course, '')
    for resource_json in resource_list:
        id = resource_type.identify_id(resource_json)
        title = resource_type.identify_title(resource_json)
        print(title)
        resource_id = "{category}/:{id}".format(category=category, id=id)
        pull_resource(resource_id, format, destination, course_name, ignore)
    return len(resource_list)


def push_resource(resource_id, format, source, course_name, ignore):
    course = Course(source, course_name)
    resource_id = ResourceID(course, resource_id)
    # Make a backup of the canvas version
    json_resource = course.pull(resource_id)
    resource_id.resource_type.extra_pull(course, resource_id)
    course.backup_json(resource_id, json_resource)
    # Load the local copy and push it to the server
    resource = course.from_disk(resource_id)
    json_resource = course.to_json(resource_id, resource)
    #pprint(json_resource)
    course.push(resource_id, json_resource)
    resource.extra_push(course, resource_id)


def pull_resource(resource_id, format, destination, course_name, ignore):
    '''
    If resource_id is a number
    '''
    if isinstance(course_name, str):
        course = Course(destination, course_name)
    else:
        course = course_name
    resource_id = ResourceID(course, resource_id)
    # Save the version from the server
    json_resource = course.pull(resource_id)
    resource = course.from_json(resource_id, json_resource)
    course.to_disk(resource_id, resource)


def publicize_resource(resource_id, format, destination, course_name, ignore):
    if isinstance(course_name, str):
        course = Course(destination, course_name)
    else:
        course = course_name
    resource_id = ResourceID(course, resource_id)
    # Find the resource on disk
    resource = course.from_disk(resource_id)
    public_resource = course.to_public(resource_id, resource)
    course.publicize(resource_id, public_resource)


def build_from_template(path, destination, course_name, ignore):
    if isinstance(course_name, str):
        course = Course(destination, course_name)
    else:
        course = course_name
    # Find the YAML file
    search_path = os.path.join(destination, Page.canonical_category, '**', path)
    potentials = glob(search_path, recursive=True)
    if not potentials:
        raise WaltzException("File not found: "+path)
    elif len(potentials) > 1:
        raise WaltzException("Too many files found: "+'\n'.join(potentials))
    yaml_path = potentials[0]
    with open(yaml_path) as yaml_file:
        yaml_data = yaml.load(yaml_file)
    # Figure out template
    template_name = yaml_data['_template']
    # Render the template
    markdown_page = course.render(template_name, yaml_data)
    # Figure out where we should store it
    path, currently = os.path.splitext(yaml_path)
    output_path = path+'.md'
    # And store it
    with open(output_path, 'w') as output_file:
        output_file.write(markdown_page)


def main(args):
    global quiet
    load_settings(args.settings)
    
    if not args.ignore:
        requests_cache.install_cache('waltz_cache')
    
    # Override default course
    if args.course:
        course = args.course
        if course not in get_courses():
            raise Exception("Unknown course name: {}".format(course))
    else:
        course = get_setting('course')
    
    if args.destination is None:
        destination = 'courses/{}/'.format(course)
        if not os.path.exists('courses/'):
            os.makedirs('courses/', exist_ok=True)
    else:
        destination = args.destination
    
    # Handle quiet
    global_settings['quiet'] = args.quiet

    # Handle the dates exporting
    if args.verb == 'pull':
        if args.id is None:
            successes = pull_all_resources(args.format, destination, 
                                           args.course, args.ignore)
            log("Finished", len(successes), "reports.")
            log(sum(map(bool, successes)), "were successful.")
        elif args.id.endswith("/*"):
            count = pull_all_resources(args.id, args.format, destination,
                                       args.course, args.ignore)
            log("Finished", count, "pulls.")
        else:
            pull_resource(args.id, args.format, destination,
                          args.course, args.ignore)
    if args.verb == 'push':
        if args.id is None:
            pass
        else:
            push_resource(args.id, args.format, destination,
                          args.course, args.ignore)
    if args.verb == 'build':
        build_from_template(args.id, destination, args.course, args.ignore)
    if args.verb == 'publicize':
        publicize_resource(args.id, args.format, destination,
                        args.course, args.ignore)