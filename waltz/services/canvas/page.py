from waltz.resource import Resource


class CanvasPage(Resource):
    """
    DOWNLOAD: gets a copy of the raw JSON version of this from Canvas
    PULL: DOWNLOAD as JSON, then RESTYLE into Markdown
    PUSH: RESTYLE from Markdown into JSON, then UPLOAD
    UPLOAD: sends the copy of the raw JSON version of this into Canvas
    EXTRACT: RESTYLE from HTML to YAML using a template
    BUILD: RESTYLE from YAML to HTML using a template
    """
    styles = ['json', 'markdown', 'html', 'yaml']


