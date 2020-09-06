from html.parser import HTMLParser
from io import StringIO
from pprint import pprint

from html2text import HTML2Text
from markdown import Markdown
import frontmatter
from frontmatter.default_handlers import YAMLHandler

# HTML to MARKDOWN
# h2m
from waltz.tools import yaml

html_to_markdown = HTML2Text()
html_to_markdown.single_line_break= False
html_to_markdown.skip_internal_links = False
html_to_markdown._skip_a_class_check = False
html_to_markdown._class_stack = []

WALTZ_METADATA_CLASS = "-waltz-metadata-hidden"


class ExtractWaltzMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.inside_metadata = False
        self.strict = False
        self.convert_charrefs = True
        self.data = []

    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            for name, value in attrs:
                if name == 'class' and WALTZ_METADATA_CLASS in value.split():
                    self.inside_metadata = True

    def handle_endtag(self, tag):
        if tag == 'div':
            self.inside_metadata = False

    def handle_data(self, data):
        if self.inside_metadata:
            self.data.append(data)


def handle_custom_tags(self, tag, attrs, start):
    if self._skip_a_class_check:
        return False
    if start:
        self._class_stack.append(attrs)
    else:
        attrs = self._class_stack.pop()
    if tag in ['i'] and not self.ignore_emphasis:
        if 'class' in attrs:
            icon = attrs['class']
            if icon.startswith('icon-'):
                if start:
                    self.o("&"+icon+";")
                    return True
                else:
                    return True
    if tag == "iframe":
        if start:
            self.o("<iframe {}>".format(" ".join(
                ['{}="{}"'.format(k, v) for k,v in
                 attrs.items()]
            )))
        else:
            self.o("</iframe>")
    if tag == "div":
        # TODO: add matching behavior on other side of m2h
        if "class" in attrs and WALTZ_METADATA_CLASS in attrs['class'].split(" "):
            #styles = [style.lower().strip() for style in attrs.get('style', '').split(";")]
            #if any(style.startswith('display') and style.endswith('none') for style in styles):
            #if not start:
            #    stream = StringIO()
            #    yaml.dump(self._waltz_data, stream)
            #    self.out("\n"+stream.getvalue()+"\n")
            #    self._waltz_data = None
            #self.out("---\n")
            if start:
                self.quiet += 1
            else:
                self.quiet -= 1
    if tag == "p" and 'class' in attrs:
        if not start:
            self._skip_a_class_check = True
            self.handle_tag(tag, attrs, start)
            self._skip_a_class_check = False
            classes= " ".join(["."+cls for cls in attrs['class'].split(" ")])
            self.outtextf("\n{: "+classes+"}")
    if tag == "a":
        if not start and 'class' in attrs:
            # Clumsy hack to prevent rechecking this tag!
            self._skip_a_class_check = True
            self.handle_tag(tag, attrs, start)
            self._skip_a_class_check = False
            classes= " ".join(["."+cls for cls in attrs['class'].split(" ")])
            self.o("{: "+classes+"}")
            return True
    if tag == "pre":
        if start:
            self.out("\n```")
            if "class" in attrs:
                if "highlight-source-java" in attrs["class"]:
                    self.out("java")
                if "highlight-source-python" in attrs["class"]:
                    self.out("python")
                else:
                    self.out("html")
            else:
                self.out("python")
            self.startpre = 0
            self.pre = 1
        else:
            self.pre = 0
            self.out("\n```")
    else:
        return False


html_to_markdown.tag_callback = handle_custom_tags


def add_to_front_matter(markdown, yaml):
    if markdown.startswith("---"):
        data = frontmatter.loads(markdown, handler=yaml)
        regular_metadata = data.metadata
        if 'waltz' not in regular_metadata:
            regular_metadata['waltz'] = {}
        regular_metadata['waltz'].update(yaml)
        yaml = regular_metadata
        markdown = data.content
    else:
        yaml = {'waltz': yaml}
    return inject_yaml(markdown, yaml)


def inject_yaml(markdown, yaml_data):
    stream = StringIO()
    yaml.dump(yaml_data, stream)
    return "---\n{}---\n{}".format(stream.getvalue(), markdown)


def h2m(html, waltz_front_matter=None):
    if not html and not waltz_front_matter:
        return ""
    # Handle front matter
    if waltz_front_matter is None:
        waltz_front_matter = {}
    #html_to_markdown._waltz_data = {'waltz': waltz_front_matter}
    metadata = ExtractWaltzMetadata()
    metadata.feed(html)
    if metadata.data:
        existing_front_matter = "\n".join(metadata.data)
        existing_front_matter = yaml.load(StringIO(existing_front_matter))
    else:
        existing_front_matter = {}
    if waltz_front_matter:
        existing_front_matter.update({'waltz': waltz_front_matter})
    markdowned = html_to_markdown.handle(html)
    in_fenced_code = False
    skip = 0
    modified = []
    for line in markdowned.split("\n"):
        if line.lstrip().startswith("```"):
            in_fenced_code = not in_fenced_code
            skip = 2 * in_fenced_code
            modified.append(line)
        elif skip:
            skip -= 1
        elif in_fenced_code:
            line = line[4:]
            modified.append(line)
        else:
            modified.append(line)
    markdowned = ("\n".join(modified)).strip()
    if existing_front_matter:
        markdowned = inject_yaml(markdowned, existing_front_matter)
    return markdowned
  
# Markdown to HTML
# m2h


my_extras = {
    'fenced-code-blocks': {
        'linenos': False,
        'noclasses': True
    },
    'html-classes': {'a': 'test'},
    #'header-ids': True,
    'tables': True
}

extension_directory='waltz.tools.'
markdowner = Markdown(extensions=[
    'fenced_code', 'attr_list',
    #'meta', # Using python-frontmatter instead
    'tables', 'codehilite', "toc",
    extension_directory+'iconfonts:IconFontsExtension',
    extension_directory+'decorate_tables:TableDecoratorExtension'
], extension_configs={
    'codehilite': {
        'noclasses': True,
        'linenums': True,
}})


def m2h(text):
    return markdowner.reset().convert(text)


class RuamelYamlHandler(YAMLHandler):
    def load(self, fm, **kwargs):
        return yaml.load(StringIO(fm))


def extract_front_matter(text):
    data = frontmatter.loads(text, handler=RuamelYamlHandler())
    regular_metadata = data.metadata
    front_matter_metadata = regular_metadata.pop('waltz', {})
    return regular_metadata, front_matter_metadata, data.content


def hide_data_in_html(data, html: str):
    if data:
        stream = StringIO()
        yaml.dump(data, stream)
        return '<div class="{tag}" style="display: none;">{data}</div>{html}'.format(
            tag=WALTZ_METADATA_CLASS,
            data=stream.getvalue(),
            html=html
        )
    else:
        return html


def dump_front_matter(front_matter, body):
    pass


def main():
    print(h2m("<i>Hello</i>"))
    print(m2h("_Hello_"))
    print(m2h("---\na:0\n---\nHello *there* you\n\nWhat's up"))
    print(repr(h2m("<p>Oh I wrote something!</p>\n<p>Here's another line.</p>")))

    return

    import os
    import argparse
    from glob import glob


    parser = argparse.ArgumentParser(description='Convert html/markdown')
    parser.add_argument('input', help='What file to read as input')
    parser.add_argument('--output', '-o', help='Where to store file (defaults to same folder as input).')
    parser.add_argument('--roundtrip', '-r', help='Whether to roundtrip the files once (e.g., HTML -> Markdown -> HTML -> Markdown', action='store_true', default=False)
    args = parser.parse_args()

    if '*' in args.input:
        input_paths = glob(args.input, recursive=True)
    else:
        input_paths = [args.input]

    for input_path in input_paths:

        path, currently = os.path.splitext(input_path)

        if currently[1:] not in ('html', 'md'):
            raise ValueError("Needed either .html or .md, but got: "+input_path)

        conversion = h2m if currently[1:] == 'html' else m2h
        convert_back = m2h if currently[1:] == 'html' else h2m
        new_extension = '.md' if currently[1:] == 'html' else '.html'

        if args.output:
            output_path = args.output
        else:
            output_path = path+new_extension
            print(output_path)

        with open(input_path) as input_file:
            contents = input_file.read()

        contents = conversion(contents)

        if args.roundtrip:
            contents = conversion(convert_back(contents))

        with open(output_path, 'w') as output_file:
            output_file.write(contents)

if __name__ == '__main__':
    main()