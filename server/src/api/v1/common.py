""" This module contains common helpers to be used in API v1 routes
"""
from rdfm.schema.v1.error import ApiError
import functools
import traceback


def api_error(error_str: str, code: int):
    """Creates an error response to be returned from an API route

    Args:
        error_str: Brief explanation of an error returned in the response
        code: HTTP status code to return
    """
    return ApiError.Schema().dump(ApiError(error=error_str)), code


def wrap_api_exception(message: str):
    def _wrap_api_exception(f):
        @functools.wraps(f)
        def __wrap_api_exception(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                print("Exception:", repr(e), flush=True)
                return api_error(message, 500)
        return __wrap_api_exception
    return _wrap_api_exception
