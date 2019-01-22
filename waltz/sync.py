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
from waltz.resources import RESOURCE_CATEGORIES, Quiz, WaltzException
    
quiet = True
def log(*args):
    if not quiet:
        print(*args)

#multiple_dropdowns_question

def download_all_resources(format, filename, course, ignore):
    quizzes = get('quizzes', all=True, course=course)

def identify_resource(resource_id):
    category, name = resource_id.split("/")
    category = category.lower()
    if category not in RESOURCE_CATEGORIES:
        raise WaltzException("Category not found: "+resource_id)
    ResourceType = RESOURCE_CATEGORIES[category]
    return ResourceType, name

def push_resource(resource_id, format, source, course, ignore):
    ResourceType, name = identify_resource(resource_id)
    

UNRESOLVED_FLAG = "# Unresolved changes!"
def pull_resource(resource_id, format, destination, course, ignore):
    '''
    If resource_id is a number
    '''
    ResourceType, name = identify_resource(resource_id)
    new_resource = ResourceType.pull(course, name)
    resource_filename = new_resource.get_safe_filename(destination)
    backups
    if format == "yaml":
        ensure_dir(resource_filename)
        if os.path.exists(resource_filename):
            with open(resource_filename, 'r') as original_version:
                old_contents = original_version.read()
                if old_contents.startswith(UNRESOLVED_FLAG):
                    log("Unresolved changes in", resource_id)
                    log("Merge before pull again!")
                    return
                old_resource = ResourceType.from_yaml(old_contents)
            differences, unresolved = new_resource.diff(old_resource)
        with open(resource_filename, 'w') as out:
            if not unresolved:
                new_resource = new_resource.to_yaml()
                walk_tree(new_resource)
                yaml.dump(new_resource, out)
            else:
                differences.yaml_set_start_comment("Unresolved changes!")
                walk_tree(differences)
                yaml.dump(differences, out)

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
