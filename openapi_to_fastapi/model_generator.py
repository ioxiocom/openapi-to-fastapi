import importlib.util
import tempfile
import uuid
from contextlib import contextmanager, suppress
from pathlib import Path

from datamodel_code_generator import DatetimeClassType, PythonVersion
from datamodel_code_generator.model import pydantic_v2 as pydantic_model
from datamodel_code_generator.parser.openapi import OpenAPIParser
from datamodel_code_generator.types import StrictTypes

from openapi_to_fastapi.logger import logger


def generate_model_from_schema(
    schema: str,
    format_code: bool = False,
    strict_validation: bool = False,
) -> str:
    """
    Given an OpenAPI schema, generate pydantic models from everything defined
    in the "components/schemas" section

    :param schema: Content of an OpenAPI spec, plain text
    :param format_code: Whether to format generated code
    :param strict_validation: Whether to use strict validation
    :return: Importable python code with generated models
    """
    if strict_validation:
        strict_types = (
            StrictTypes.str,
            StrictTypes.bytes,
            StrictTypes.int,
            StrictTypes.float,
            StrictTypes.bool,
        )
    else:
        strict_types = None

    if strict_validation:
        target_datetime_class = DatetimeClassType.Awaredatetime
    else:
        target_datetime_class = DatetimeClassType.Datetime

    parser = OpenAPIParser(
        source=schema,
        data_model_type=pydantic_model.BaseModel,
        data_model_root_type=pydantic_model.RootModel,
        data_type_manager_type=pydantic_model.DataTypeManager,
        data_model_field_type=pydantic_model.DataModelField,
        base_class="pydantic.BaseModel",
        custom_template_dir=None,
        extra_template_data=None,
        target_python_version=PythonVersion.PY_39,
        dump_resolve_reference_action=None,
        extra_fields="forbid" if strict_validation else None,
        strict_types=strict_types,
        field_constraints=False,
        snake_case_field=False,
        strip_default_none=False,
        aliases=None,
        target_datetime_class=target_datetime_class,
    )

    result = str(parser.parse(format_=format_code))

    if strict_validation:
        result = override_with_stricter_dates(result)

    return result


@contextmanager
def _clean_tempfile(tmp_file, delete=True):
    try:
        yield tmp_file
    finally:
        if delete:
            tmp_file.close()
            with suppress(FileNotFoundError):
                Path(tmp_file.name).unlink()


def load_models(
    schema: str,
    name: str = "",
    cleanup: bool = True,
    format_code: bool = False,
    strict_validation: bool = False,
):
    """
    Generate pydantic models from OpenAPI spec and return a python module,
    which contains all the models from the "components/schemas" section.
    This function will create a dedicated python file in OS's temporary dir
    and imports it.

    :param schema: OpenAPI spec, plain text
    :param name: Prefix for a module name, optional
    :param cleanup: Whether to remove a file with models afterwards
    :param format_code: Whether to format generated code
    :param strict_validation: Whether to use strict validation
    :return: Module with pydantic models
    """
    prefix = name.replace("/", "").replace(" ", "").replace("\\", "") + "_"
    with _clean_tempfile(
        tempfile.NamedTemporaryFile(
            prefix=prefix, mode="w", suffix=".py", encoding="utf8", delete=False
        ),
        delete=cleanup,
    ) as tmp_file:
        model_py = generate_model_from_schema(schema, format_code, strict_validation)
        tmp_file.write(model_py)
        if not cleanup:
            logger.info("Generated module %s: %s", name, tmp_file.name)
        tmp_file.flush()
        module_name = f"oas_models_{uuid.uuid4()}"
        spec = importlib.util.spec_from_file_location(module_name, tmp_file.name)
        if spec and spec.loader:
            return spec.loader.load_module(module_name)
        else:
            raise ValueError(f"Failed to load module {module_name}")


def override_with_stricter_dates(file_content: str) -> str:
    """
    Overrides the AwareDatetime and date in the python file by identifying the first
    class definition (after the imports at the top) and injecting a comment and then
    importing the StrictAwareDatetime as AwareDatetime and StrictDate as date which will
    thus override the earlier imports.

    Example of the file before applying changes:
    > from __future__ import annotations
    > from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, ...
    > from typing import List, Optional, Union
    > from datetime import date
    >
    >
    > class BadGateway(BaseModel):
    >     pass
    >     ...

    Example of file after changes:
    > from __future__ import annotations
    > from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictInt, ...
    > from typing import List, Optional, Union
    > from datetime import date
    >
    > # Overriding the AwareDatetime and date with ones that do stricter validation
    > from openapi_to_fastapi.pydantic_validators import StrictAwareDatetime as Aware...
    > from openapi_to_fastapi.pydantic_validators import StrictDate as date
    >
    >
    > class BadGateway(BaseModel):
    >     pass
    >     ...

    :param file_content: The file content as a string.
    :return: The modified file content as a string.
    """
    comment = (
        "# Overriding the AwareDatetime and date with ones that do stricter validation"
    )
    import_strict_date_time = (
        "from openapi_to_fastapi.pydantic_validators import "
        "StrictAwareDatetime as AwareDatetime"
    )
    import_strict_date = (
        "from openapi_to_fastapi.pydantic_validators import StrictDate as date"
    )

    if "AwareDatetime" in file_content or "date" in file_content:
        newline = "\n"
        if "\r\n" in file_content:
            newline = "\r\n"

        parts = file_content.partition(f"{newline}{newline}class ")
        file_content = (
            f"{parts[0]}{newline}"
            f"{comment}{newline}"
            f"{import_strict_date_time}{newline}"
            f"{import_strict_date}{newline}"
            f"{parts[1]}{parts[2]}"
        )

    return file_content
