from waltz.resource import Resource


class Page(Resource):
    """
    DOWNLOAD: gets a copy of the raw JSON version of this from Canvas
    PULL: DOWNLOAD as JSON, then RESTYLE into Markdown
    PUSH: RESTYLE from Markdown into JSON, then UPLOAD
    UPLOAD: sends the copy of the raw JSON version of this into Canvas
    EXTRACT: RESTYLE from HTML to YAML using a template
    BUILD: RESTYLE from YAML to HTML using a template
    """
    data: 'Dict[str, Any]'
    category_names = ['page', 'pages']
    styles = ['json', 'markdown', 'html', 'templated']

    def __init__(self, raw):
        self.data = {
            'json': None,
            'markdown': None,
            'html': None,
            'templated': None
        }

    def search(self, resource, service):
        pass

    def __str__(self):
        return "<Page {}>".format(self.raw)

    def upload_to_canvas(self, service):
        # Take the DB version of this resource and send it to the canvas service
        pass

    def download_from_canvas(self, service):
        pass

    def from_json_to_markdown(self, services):
        # Take the DB version of this resource and send it to the local service,
        # restyle it along the way
        pass

    def from_markdown_to_json(self, services):
        pass

    def from_json_to_preview(self):
        pass

'''

category_names = ["page", "pages"]
    canvas_name = 'pages'
    canonical_category = 'pages'
    canvas_title_field = 'title'
    canvas_id_field = 'url'
    extension = '.md'

    def from_json(cls, course, json_data):
        if 'body' not in json_data:
            data = get('{}/{}'.format(cls.canvas_name, json_data['url']),
                       course=course.course_name)
            json_data['body'] = data['body']
        return cls(**json_data, course=course)
    
    def to_disk(self, resource):
        return h2m(self.body)
    
    @classmethod
    def from_disk(cls, course, resource_data, resource_id):
        # Fix configuration on simpler attributes
        return cls(body=m2h(resource_data), course=course,
                   title=resource_id.canvas_title)
    
    def to_json(self, course, resource_id):
        #Suitable for PUT request on API
        return {
            'wiki_page[body]': self.body,
            'wiki_page[title]': self.title
        }
        '''