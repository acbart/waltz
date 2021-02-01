class WaltzException(Exception):
    def __init__(self, message, *args):
        self.args = args
        self.message = message

    def __str__(self):
        return self.message


class WaltzServiceNotFound(WaltzException):
    pass


class WaltzAmbiguousResource(WaltzException):
    pass


class WaltzResourceNotFound(WaltzException):
    pass
