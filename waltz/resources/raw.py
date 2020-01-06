class RawResource:
    service: str
    category: str
    title: str
    disambiguate: str
    data: str

    def __init__(self, service, category, title, disambiguate, data):
        self.service = service
        self.category = category
        self.title = title
        self.disambiguate = disambiguate
        self.data = data

    @classmethod
    def from_database(cls, row):
        return RawResource(*row)
