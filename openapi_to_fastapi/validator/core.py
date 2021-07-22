import abc
import json
from pathlib import Path
from typing import Union


class ValidationError(Exception):
    pass


class OpenApiValidationError(ValidationError):
    pass


class InvalidJSON(OpenApiValidationError):
    pass


class UnsupportedVersion(OpenApiValidationError):
    pass


class MissingParameter(OpenApiValidationError):
    pass


class BaseValidator:
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)

    def validate(self):
        try:
            spec = json.loads(self.path.read_text(encoding="utf8"))
        except json.JSONDecodeError:
            raise InvalidJSON(f"Incorrect JSON: {self.path}")
        except Exception as e:
            raise ValidationError(f"Failed to validate {self.path}: {e}")
        self.validate_spec(spec)

    @abc.abstractmethod
    def validate_spec(self, spec: dict):
        raise NotImplementedError


class DefaultValidator(BaseValidator):
    def validate_spec(self, spec: dict):
        if not spec.get("openapi", "").startswith("3"):
            raise UnsupportedVersion
