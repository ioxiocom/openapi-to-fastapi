import inspect
from copy import deepcopy
from types import FunctionType
from typing import Callable, Type

import pydantic


def copy_function(fn) -> Callable:
    """
    Create a clone of a given function
    :param fn: Function to copy
    :return: New function with the same attributes but with different id
    """
    """Based on http://stackoverflow.com/a/6528148/190597 (Glenn Maynard)"""
    g = FunctionType(
        fn.__code__,
        fn.__globals__,
        name=fn.__name__,
        argdefs=fn.__defaults__,
        closure=fn.__closure__,
    )
    g.__kwdefaults__ = deepcopy(fn.__kwdefaults__)
    g.__annotations__ = deepcopy(fn.__annotations__)
    return g


def add_annotation_to_first_argument(fn: FunctionType, model: Type[pydantic.BaseModel]):
    """
    Patch given function so its first argument without type annotation
    becomes type-hinted with model
    :param fn: Function to patch
    :param model: Type to add to the first argument
    """
    fn_spec = inspect.getfullargspec(fn)
    if not len(fn_spec.args):
        raise ValueError(f"Function {fn.__name__} has no arguments")
    untyped_args = [a for a in fn_spec.args if a not in fn.__annotations__]
    if untyped_args:
        fn.__annotations__[untyped_args[0]] = model
