import re
from datetime import date
from typing import Annotated, Any

from pydantic import AwareDatetime, BeforeValidator
from pydantic_core import PydanticCustomError

rfc_3339_pattern = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(Z|[\+-]\d{2}:\d{2})$"
)

year_month_day_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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

        raise PydanticCustomError(
            "datetime_type",
            "Input should be a valid datetime in RFC 3339 format, input is not a "
            "string",
            {"error": "input not string"},
        )

    if not re.match(rfc_3339_pattern, value):
        # Validates the format of the string strictly, but leaves things like how many
        # days there is in a month, or hours in a day, etc. to AwareDatetime to check.
        raise PydanticCustomError(
            "datetime_from_date_parsing",
            "Input should be a valid datetime, in RFC 3339 format",
            {"error": "input does not follow RFC 3339"},
        )

    return value


def strict_date_validator(value: Any) -> str:
    """
    A function to be used as an extra before validator for a stricter validation of
    dates.

    It aims to only allow dates of the form YYYY-MM-DD.

    :param value: The value provided for the field.
    :return: The string unchanged after validation.
    """
    # When the before validators run, pydantic has not made any validation of the field
    # just yet. The content can really be of any kind.
    if not isinstance(value, str):
        # This will (also) catch integers that would else be parsed as unix timestamps.

        raise PydanticCustomError(
            "date_type",
            "Input should be a valid date in RFC 3339 'full-date' format, input is not "
            "a string",
            {"error": "input not string"},
        )

    if not re.match(year_month_day_pattern, value):
        # Validates the format of the string strictly, but leaves things like how many
        # days there is in a month to the normal date class.
        raise PydanticCustomError(
            "date_from_datetime_parsing",
            "Input should be a valid date, in RFC 3339 'full-date' format",
            {"error": "input is not of form YYYY-MM-DD"},
        )

    return value


StrictAwareDatetime = Annotated[
    AwareDatetime, BeforeValidator(strict_datetime_validator)
]


StrictDate = Annotated[date, BeforeValidator(strict_date_validator)]
