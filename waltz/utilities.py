import os
import re
from datetime import datetime
from dateutil import tz, parser
from textwrap import indent
import pathlib

from waltz.canvas_tools import from_canvas_date, to_canvas_date

def ensure_dir(file_path):
    pathlib.Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)
    #directory = os.path.dirname(file_path)
    #if not os.path.exists(directory):
        #os.makedirs(directory)

def clean_name(filename):
    return "".join([c for c in filename
                    if c.isalpha() or c.isdigit() 
                       or c in (' ', '.')]).rstrip()
                       
def make_safe_filename(name):
    # Based on https://stackoverflow.com/a/46801075/1718155
    filename = str(name).strip()
    filename = re.sub(r'(?u)[^-\w. ]', '', filename)
    return filename

def make_datetime_filename():
    return datetime.now().strftime('%Y-%b-%d_%H-%M-%S')

def indent4(text):
    return indent(text, '    ')
    
global_settings = {'quiet': True}
def log(*args):
    if not global_settings['quiet']:
        print(*args)

FRIENDLY_DATE_FORMAT = "%B %d %Y, %I%M %p"
from_zone = tz.tzutc()
to_zone = tz.tzlocal()
def to_friendly_date(canvas_date_string):
    if not canvas_date_string:
        return ''
    return (from_canvas_date(canvas_date_string)
                      .replace(tzinfo=from_zone)
                      .astimezone(to_zone)
                      .strftime(FRIENDLY_DATE_FORMAT))


def from_friendly_date(friendly_date_string):
    if not friendly_date_string:
        return ''
    return to_canvas_date(parser.parse(friendly_date_string)
                                .replace(tzinfo=to_zone)
                                .astimezone(from_zone))
