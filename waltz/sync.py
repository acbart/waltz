import json
import os
import math
import requests
import requests_cache
import argparse
import re
import csv
import dateutil.parser
from datetime import datetime
from pprint import pprint
from collections import Counter, defaultdict
try:
    from tqdm import tqdm
except:
    print("TQDM is not installed. No progress bars will be available.")
    tqdm = list

from deepdiff import DeepDiff

from waltz.yaml_setup import yaml
from ruamel.yaml.scalarstring import walk_tree
    
from waltz.canvas_tools import get, post, put, delete, progress_loop
from waltz.canvas_tools import get_setting, get_courses, download_file
from waltz.canvas_tools import from_canvas_date, to_canvas_date
from waltz.canvas_tools import yaml_load, load_settings
from waltz.utilities import ensure_dir
from waltz.resources import RESOURCE_CATEGORIES, ResourceID, WaltzException, Course
    
quiet = True
def log(*args):
    if not quiet:
        print(*args)

#multiple_dropdowns_question

def download_all_resources(format, filename, course, ignore):
    quizzes = get('quizzes', all=True, course=course)

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
    course.push(resource_id, json_resource)
    resource.extra_push(course, resource_id)

UNRESOLVED_FLAG = "# Unresolved changes!"
def pull_resource(resource_id, format, destination, course_name, ignore):
    '''
    If resource_id is a number
    '''
    course = Course(destination, course_name)
    resource_id = ResourceID(course, resource_id)
    # Make a backup of the local version
    course.backup_resource(resource_id)
    # Save the version from the server
    json_resource = course.pull(resource_id)
    resource = course.from_json(resource_id, json_resource)
    course.to_disk(resource_id, resource)

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
            os.makedirs(path, exist_ok=True)
    else:
        destination = args.destination
    
    # Handle quiet
    quiet = args.quiet

    # Handle the dates exporting
    if args.verb == 'pull':
        if args.id is None:
            successes = download_all_resources(args.format, args.destination, 
                                               args.course, args.ignore)
            log("Finished", len(successes), "reports.")
            log(sum(map(bool, successes)), "were successful.")
        else:
            pull_resource(args.id, args.format, destination,
                          args.course, args.ignore)
    if args.verb == 'push':
        if args.id is None:
            pass
        else:
            push_resource(args.id, args.format, destination,
                          args.course, args.ignore)
