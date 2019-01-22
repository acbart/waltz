from html2text import HTML2Text
from markdown import markdown

# HTML to MARKDOWN
# h2m

html_to_markdown = HTML2Text()
html_to_markdown.single_line_break= False
html_to_markdown._kept_classes = []
html_to_markdown._skip_a_class_check = False

def handle_custom_tags(self, tag, attrs, start):
    if self._skip_a_class_check:
        return False
    if tag == "a":
        if start and "class" in attrs and attrs["class"].startswith("icon-"):
            self._kept_classes.append(attrs["class"])
        elif start:
            self._kept_classes.append(None)
        if not start:
            icon = self._kept_classes.pop()
            if icon is not None:
                self._skip_a_class_check = True
                self.handle_tag(tag, attrs, start)
                self._skip_a_class_check = False
                self.o("{: class="+icon+"}")
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
    m = html_to_markdown.handle(html)
    in_fenced_code = False
    skip = 0
    modified = []
    print(repr(m))
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
    return "\n".join(modified)
  
## Markdown to HTML
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
def markdowner(text):
    return markdown(text, extensions=[
        'fenced_code', 'attr_list',
        'tables', 'codehilite',
    ], extension_configs={
        'codehilite': {
        'noclasses': True
    }})

m2h = markdowner
