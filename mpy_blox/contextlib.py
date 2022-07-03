class suppress:
    def __init__(self, *exceptions):
        self.suppressed_excs = exceptions

    def __enter__(self):
        pass  # NO-OP

    def __exit__(self, exc_type, exc_val, tb):
        return (exc_type is not None
                and issubclass(exc_type, self.suppressed_excs))