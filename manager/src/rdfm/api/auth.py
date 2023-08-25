from requests.auth import AuthBase


class DefaultAuth(AuthBase):
    """ Authorization stub for the RDFM API

    This should be replaced once the API auth has been formalized
    """

    def __init__(self):
        pass

    def __call__(self, r):
        return r
