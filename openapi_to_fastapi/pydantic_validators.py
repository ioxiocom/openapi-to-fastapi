import re
from typing import Annotated, Any

from pydantic import AwareDatetime, BeforeValidator
from pydantic_core import PydanticCustomError

year_dash_pattern = re.compile(r"^\d{4}-")


def strict_datetime_validator(value: Any) -> str:
    """
    A function to be used as an extra before validator for a stricter version of the
    AwareDatetime provided by pydantic.

    It aims to (together with AwareDatetime) only allow valid RFC 3339 date times.

    :param value: The value provided for the field.
    :return: The string unchanged after validation.
    """
    # When the before validators run, pydantic has not made any validation of the field
    # just yet. The content can really be of any kind.
    if not isinstance(value, str):
        # This will (also) catch integers that would else be parsed as unix timestamps.

        # This is derived from similar errors pydantic raises when validating date
        # times.
        raise PydanticCustomError(
            "datetime_from_date_parsing",
            "Input should be a valid datetime or date, input is not a string",
            {"error": "input not string"},
        )

    if not re.match(year_dash_pattern, value):
        # Merely check the string starts with a valid pattern, like YYYY-. A string of
        # only digits would be parsed as a unix timestamp by AwareDatetime. The rest of
        # the validation of the string is left to AwareDatetime.

        # This mimics the error pydantic raises for partial strings.
        raise PydanticCustomError(
            "datetime_from_date_parsing",
            "Input should be a valid datetime or date, input is too short",
            {"error": "input is too short"},
        )

    return value


StrictAwareDatetime = Annotated[
    AwareDatetime, BeforeValidator(strict_datetime_validator)
]
