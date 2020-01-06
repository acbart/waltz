try:
    from tqdm import tqdm
except ImportError:
    print("TQDM is not installed. No progress bars will be available.")
    tqdm = list

from jinja2 import Template

from waltz.tools.yaml_setup import yaml


def to_markdown(yaml_path, template_path):
    path, currently = os.path.splitext(yaml_path)
    output_path = path + '.md'

    with open(yaml_path) as yaml_file:
        yaml_data = yaml.load(yaml_file)

    with open(template_path) as template_file:
        raw_template = template_file.read()

    template = Template(raw_template)
    markdown_page = template.render(**yaml_data)

    with open(output_path, 'w') as output_file:
        output_file.write(markdown_page)


if __name__ == '__main__':
    import os
    import argparse

    parser = argparse.ArgumentParser(description='Build Markdown page from YAML')
    parser.add_argument('input', help='What file to read as input')
    parser.add_argument('template', help='The path to the desired template file')
    args = parser.parse_args()

    to_markdown(args.input, args.template)
