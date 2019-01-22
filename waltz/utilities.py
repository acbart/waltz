import os
import re
from datetime import datetime
from textwrap import indent

def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

def clean_name(filename):
    return "".join([c for c in filename
                    if c.isalpha() or c.isdigit() 
                       or c in (' ', '.')]).rstrip()
                       
def make_safe_filename(name):
    # Based on https://stackoverflow.com/a/46801075/1718155
    filename = str(name).strip().replace(' ', '_')
    filename = re.sub(r'(?u)[^-\w.]', '', filename)
    return filename

def make_datetime_filename():
    return datetime.now().strftime('%Y-%b-%d_%H-%M-%S')

def indent4(text):
    return indent(text, '    ')