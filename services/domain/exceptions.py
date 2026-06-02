class LLMTwinException(Exception):
    pass


class ImproperlyConfigured(LLMTwinException):
    pass


class NoSuchElementException(LLMTwinException):
    pass
