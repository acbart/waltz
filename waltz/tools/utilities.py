import os
import re
from datetime import datetime
from dateutil import tz, parser
from textwrap import indent
import pathlib


def ensure_dir(file_path):
    pathlib.Path(os.path.dirname(file_path)).mkdir(parents=True, exist_ok=True)


def clean_name(filename):
    return "".join([c for c in filename
                    if c.isalpha() or c.isdigit()
                    or c in (' ', '.')]).rstrip()


def make_safe_filename(name):
    # Based on https://stackoverflow.com/a/46801075/1718155
    filename = str(name).strip()
    filename = re.sub(r'(?u)[^-\w. ]', '', filename)
    return filename


def make_end_path(path):
    """ Prepends a path '../' parent markers to specify the parent
     directories of a path, but consider it locally. """
    parts = pathlib.Path(path).parts
    parent_directory_markers = parts.count('..')
    parent_prepends = '../'*(len(parts) - parent_directory_markers*2 - 1)
    final_path = os.path.join(parent_prepends, path)
    return final_path


def all_path_parts_match(full_path, end_path):
    """
    Determines that the given ``full_path`` ends with the given ``end_path``,
    correctly handling nested directories. This is a pretty simple check if
    the ``end_path`` is just a single file.

    Args:
        full_path (str):
        end_path (str):

    Returns:
        bool: Whether or not they match.
    """
    end_path_parts = pathlib.Path(end_path).parts[::-1]
    full_path_parts = pathlib.Path(full_path).parts[::-1]
    return all(left == right
               for left, right in zip(end_path_parts, full_path_parts))


def get_parent_directory(path):
    return pathlib.Path(path).parent.parent


def json_bool(boolean_value):
    return 'true' if boolean_value else 'false'


def make_datetime_filename():
    return datetime.now().strftime('%Y-%b-%d_%H-%M-%S')


def indent4(text):
    return indent(text, '    ')


CANVAS_DATE_STRING = "%Y-%m-%dT%H:%M:%SZ"
FRIENDLY_DATE_FORMAT = "%B %d %Y, %I%M %p"
from_zone = tz.tzutc()
to_zone = tz.tzlocal()


def from_canvas_date(d1):
    return datetime.strptime(d1, CANVAS_DATE_STRING)


def to_canvas_date(d1):
    return d1.strftime(CANVAS_DATE_STRING)


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


def to_friendly_date_from_datetime(d: datetime) -> str:
    return d.replace(tzinfo=from_zone).astimezone(to_zone).strftime(FRIENDLY_DATE_FORMAT)


def datetime_to_blockpy_string(a_datetime):
    return a_datetime.isoformat() + 'Z'


def blockpy_string_to_datetime(a_string):
    try:
        return datetime.strptime(a_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        return datetime.strptime(a_string, '%Y-%m-%dT%H:%M:%SZ')


def get_files_last_update(source_path) -> datetime:
    return datetime.fromtimestamp(os.path.getmtime(source_path))


def start_file(filename):
    '''Open document with default application in Python.'''
    try:
        os.startfile(filename)
    except AttributeError:
        os.subprocess.call(['open', filename])
