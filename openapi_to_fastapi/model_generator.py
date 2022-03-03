import importlib.util
import tempfile
import uuid
from contextlib import contextmanager, suppress
from pathlib import Path

from datamodel_code_generator import PythonVersion
from datamodel_code_generator.model import pydantic as pydantic_model
from datamodel_code_generator.parser.openapi import OpenAPIParser

from openapi_to_fastapi.logger import logger


def generate_model_from_schema(schema: str) -> str:
    """
    Given an OpenAPI schema, generate pydantic models from everything defined
    in the "components/schemas" section

    :param schema: Content of an OpenAPI spec, plain text
    :return: Importable python code with generated models
    """
    parser = OpenAPIParser(
        source=schema,
        data_model_type=pydantic_model.BaseModel,
        data_model_root_type=pydantic_model.CustomRootType,
        data_type_manager_type=pydantic_model.DataTypeManager,
        data_model_field_type=pydantic_model.DataModelField,
        base_class="pydantic.BaseModel",
        custom_template_dir=None,
        extra_template_data=None,
        target_python_version=PythonVersion.PY_37,
        dump_resolve_reference_action=None,
        validation=True,
        field_constraints=False,
        snake_case_field=False,
        strip_default_none=False,
        aliases=None,
    )

    result = parser.parse()
    return str(result)


@contextmanager
def _clean_tempfile(tmp_file, delete=True):
    try:
        yield tmp_file
    finally:
        if delete:
            tmp_file.close()
            with suppress(FileNotFoundError):
                Path(tmp_file.name).unlink()


def load_models(schema: str, name: str = "", cleanup: bool = True):
    """
    Generate pydantic models from OpenAPI spec and return a python module,
    which contains all the models from the "components/schemas" section.
    This function will create a dedicated python file in OS's temporary dir
    and imports it
    :param schema: OpenAPI spec, plain text
    :param name: Prefix for a module name, optional
    :param cleanup: Whether to remove a file with models afterwards
    :return: Module with pydantic models
    """
    prefix = name.replace("/", "").replace(" ", "").replace("\\", "") + "_"
    with _clean_tempfile(
        tempfile.NamedTemporaryFile(
            prefix=prefix, mode="w", suffix=".py", encoding="utf8", delete=False
        ),
        delete=cleanup,
    ) as tmp_file:
        model_py = generate_model_from_schema(schema)
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
