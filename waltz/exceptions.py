class WaltzException(Exception):
    pass


class WaltzServiceNotFound(WaltzException):
    pass


class WaltzAmbiguousResource(WaltzException):
    pass


class WaltzResourceNotFound(WaltzException):
    pass
