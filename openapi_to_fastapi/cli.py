import importlib.util
import logging
import sys
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import List

import click
import coloredlogs

from openapi_to_fastapi.validator.core import BaseValidator, DefaultValidator

from .routes import SpecRouter
from .validator import ihan_standards

logger = logging.getLogger("openapi_to_fastapi_cli")
coloredlogs.install(logger=logger, fmt="%(message)s")


def print_dashes(char="=", length=79):
    logger.info(char * length)


@contextmanager
def header():
    print_dashes()
    yield
    print_dashes()


@click.command()
@click.option(
    "--path", "-p", required=True, help="Path to directory with OpenAPI specs"
)
@click.option("--validator", "-v", multiple=True, help="Class name of extra validator")
@click.option(
    "--module",
    "-m",
    multiple=True,
    help="Module with extra validator class definitions",
)
def cli_validate_specs(path: str, validator, module):
    sys.exit(validate_specs(Path(path), module, validator))


def validate_specs(path: Path, modules: List[str], extra_validators: List[str]) -> int:
    validators = _load_validators(extra_validators, modules)
    with header():
        logger.info(f"OpenAPI specs root path: {path}")
        logger.info("Validators: %s", ", ".join([v.__name__ for v in validators]))

    passed, failed = 0, 0
    for spec_path in path.glob("**/*.json"):
        logger.info(f"File: {spec_path}")
        try:
            SpecRouter(spec_path, validators)
        except Exception:
            logger.error("\n%s", traceback.format_exc())
            logger.error("[FAILED]")
            failed += 1
        else:
            logger.info("[PASSED]")
            passed += 1
        print_dashes("-")

    with header():
        log = logger.error if failed else logger.info
        log("Summary:")
        log(f"Total : {passed+failed}")
        log(f"Passed: {passed}")
        log(f"Failed: {failed}")
    return 1 if failed else 0


def _load_extra_validator_modules(modules: List[str]) -> list:
    validator_modules = [ihan_standards]
    for module_path in modules:
        module_name = f"oas_models_{uuid.uuid4()}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec and spec.loader:
            validator_modules.append(spec.loader.load_module(module_name))
    return validator_modules


def _load_validators(
    validators: List[str],
    extra_modules: List[str],
) -> list:
    _validators = [DefaultValidator]

    for name in validators:
        for validator_module in _load_extra_validator_modules(extra_modules):
            validator = getattr(validator_module, name, None)
            if validator and issubclass(validator, BaseValidator):
                _validators.append(validator)
                break
        else:
            raise ValueError(f"Failed to load validator: {name}")
    return _validators
