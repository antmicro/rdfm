""" This module contains common helpers to be used in API v1 routes
"""
from rdfm.schema.v1.error import ApiError


def api_error(error_str: str, code: int):
    """ Creates an error response to be returned from an API route

    Args:
        error_str: Brief explanation of an error returned in the response
        code: HTTP status code to return
    """
    return ApiError.Schema().dumps(ApiError(error=error_str)), code
