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

    # Signature is immutable, no need to copy/deepcopy
    # Mypy doesn't know about __signature__: https://github.com/python/mypy/issues/12472
    g.__signature__ = inspect.signature(fn)  # type: ignore[attr-defined]

    return g


def add_annotation_to_first_argument(fn: FunctionType, model: Type[pydantic.BaseModel]):
    """
    Patch given function so its first argument without type annotation
    becomes type-hinted with model
    :param fn: Function to patch
    :param model: Type to add to the first argument
    """

    sig = inspect.signature(fn)
    params = sig.parameters
    if not params:
        raise ValueError(f"Function {fn.__name__} has no arguments")

    updated = False
    updated_params = []
    for param_name, param in params.items():
        if not updated and param.annotation is inspect.Parameter.empty:
            updated_params.append(param.replace(annotation=model))
            updated = True
        else:
            updated_params.append(param)

    # Mypy doesn't know about __signature__: https://github.com/python/mypy/issues/12472
    fn.__signature__ = sig.replace(  # type: ignore[attr-defined]
        parameters=updated_params
    )
