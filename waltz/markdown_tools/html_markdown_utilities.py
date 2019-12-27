from html2text import HTML2Text
from markdown import markdown

# HTML to MARKDOWN
# h2m

html_to_markdown = HTML2Text()
html_to_markdown.single_line_break= False
html_to_markdown.skip_internal_links = False
html_to_markdown._skip_a_class_check = False
html_to_markdown._class_stack = []

WALTZ_METADATA_CLASS = "waltz-metadata"

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
            styles = [style.lower().strip() for style in attrs.get('style', '').split(";")]
            if any(style.startswith('display') and style.endswith('none') for style in styles):
                self.out("---")
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


def h2m(html):
    if not html:
        return ""
    m = html_to_markdown.handle(html)
    in_fenced_code = False
    skip = 0
    modified = []
    for line in m.split("\n"):
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
    return ("\n".join(modified)).strip()
  
# Markdown to HTML
# m2h


my_extras = {
    'fenced-code-blocks': {
        'linenos': False,
        'noclasses': True
    },
    'html-classes': {'a': 'test'},
    'header-ids': True,
    'tables': True
}


def m2h(text, extension_directory='waltz.'):
    result = markdown(text, extensions=[
        'fenced_code', 'attr_list', 'meta',
        'tables', 'codehilite',
        extension_directory+'iconfonts:IconFontsExtension',
        extension_directory+'headerid:HeaderIdExtension',
        extension_directory+'decorate_tables:TableDecoratorExtension'
    ], extension_configs={
        'codehilite': {
        'noclasses': True
    }})
    return result


if __name__ == '__main__':
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
        
        m2h = lambda contents: m2h(contents, extension_directory='')
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
