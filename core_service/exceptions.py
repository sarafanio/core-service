class ServiceStartupException(RuntimeError):
    pass


class UnexpectedTaskException(RuntimeError):
    pass


class UnhealthyException(RuntimeError):
    pass
