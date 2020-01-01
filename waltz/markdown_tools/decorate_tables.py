
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class DecorateTablesProcessor(Treeprocessor):
    def run(self, root):
        self.set_table_class(root)
    
    def set_table_class(self, element):
        for child in element:
            if child.tag == "table":
                child.set("class", "table table-striped table-bordered")  # set the class attribute
            self.set_table_class(child)  # run recursively on children


class TableDecoratorExtension(Extension):
    def extendMarkdown(self, md, md_globals):
        # Register instance of 'mypattern' with a priority of 175
        md.registerExtension(self)
        self.processor = DecorateTablesProcessor()
        self.processor.md = md
        self.processor.config = self.getConfigs()
        md.treeprocessors.add('decorate_tables', self.processor, '>toc')


# http://pythonhosted.org/Markdown/extensions/api.html#makeextension
def makeExtension(*args, **kwargs):
    return TableDecoratorExtension(*args, **kwargs)
