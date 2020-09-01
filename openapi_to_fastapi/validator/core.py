import abc
import json
from pathlib import Path
from typing import Union


class OpenApiValidationError(Exception):
    pass


class InvalidJSON(OpenApiValidationError):
    pass


class UnsupportedVersion(OpenApiValidationError):
    pass


class MissingParameter(OpenApiValidationError):
    pass


class BaseValidator:
    def __init__(self, path: Union[str, Path]):
        if isinstance(path, str):
            self.path = Path(path)
        else:
            self.path = path

    def validate(self):
        try:
            spec = json.loads(self.path.read_text())
        except json.JSONDecodeError:
            raise InvalidJSON(f"Incorrect JSON: {self.path}")
        self.validate_spec(spec)

    @abc.abstractmethod
    def validate_spec(self, spec: dict):
        raise NotImplementedError


class DefaultValidator(BaseValidator):
    def validate_spec(self, spec: dict):
        if not spec.get("openapi", "").startswith("3"):
            raise UnsupportedVersion
