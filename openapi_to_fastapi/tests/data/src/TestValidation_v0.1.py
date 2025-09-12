from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from definition_tooling.converter import CamelCaseModel, DataProductDefinition
from pydantic import Field


class ExampleEnum(str, Enum):
    FOO = "foo"
    BAR = "bar"


class ValidationBase(CamelCaseModel):
    number_1: float = Field(
        ...,
        title="Number 1",
        description="Float with no extra validation.",
        examples=[50.5],
    )
    number_2: float = Field(
        ...,
        title="Number 2",
        description="Float 0-100.",
        ge=0.0,
        le=100.0,
        examples=[50.5],
    )
    number_3: int = Field(
        ...,
        title="Number 3",
        description="Integer with no extra validation.",
        examples=[50],
    )
    number_4: int = Field(
        ...,
        title="Number 4",
        description="Integer 0-10.",
        ge=0,
        le=10,
        examples=[5],
    )
    number_5: Optional[float] = Field(
        None,
        title="Number 5",
        description="Optional float with no extra validation.",
        examples=[50.2],
    )
    number_6: Optional[float] = Field(
        None,
        title="Number 6",
        description="Optional float 0-100.",
        ge=-0.0,
        le=100.0,
        examples=[50.3],
    )
    number_7: Optional[int] = Field(
        None,
        title="Number 7",
        description="Optional integer with no extra validation.",
        examples=[50],
    )
    number_8: Optional[int] = Field(
        None,
        title="Number 8",
        description="Optional integer 0-10.",
        ge=0,
        le=10,
        examples=[5],
    )
    bool_1: bool = Field(
        ...,
        title="Bool 1",
        description="Required boolean.",
        examples=[True],
    )
    bool_2: Optional[bool] = Field(
        None,
        title="Bool 2",
        description="Optional boolean.",
        examples=[True],
    )
    string_1: str = Field(
        ...,
        title="String 1",
        description="Required string.",
        examples=["Foo"],
    )
    string_2: str = Field(
        ...,
        title="String 2",
        max_length=10,
        description="Required string with max length 10.",
        examples=["Foo"],
    )
    string_3: Optional[str] = Field(
        None,
        title="String 3",
        description="Optional string.",
        examples=["Foo"],
    )
    string_4: Optional[str] = Field(
        None,
        title="String 4",
        min_length=1,
        max_length=10,
        description="Optional string with min length 1 and max length 10.",
        examples=["Foo"],
    )
    date_1: date = Field(
        ...,
        title="Date 1",
        description="Required date.",
        examples=[date.fromisoformat("2025-01-01")],
    )
    date_2: Optional[date] = Field(
        None,
        title="Date 2",
        description="Optional date.",
        examples=[date.fromisoformat("2025-01-01")],
    )
    datetime_1: datetime = Field(
        ...,
        title="Datetime 1",
        description="Required datetime.",
        examples=[datetime.fromisoformat("2025-01-01T00:00:00+00:00")],
    )
    datetime_2: Optional[datetime] = Field(
        None,
        title="Datetime 2",
        description="Optional datetime.",
        examples=[datetime.fromisoformat("2025-01-01T00:00:00+00:00")],
    )
    enum_1: ExampleEnum = Field(
        ...,
        title="Enum 1",
        description="Required enum.",
        examples=[ExampleEnum.FOO],
    )
    enum_2: Optional[ExampleEnum] = Field(
        None,
        title="Enum 2",
        description="Optional enum.",
        examples=[ExampleEnum.BAR],
    )
    list_str: List[str] = Field(
        ...,
        title="List strings",
        description="List of string.",
        examples=[["abc", "def"]],
    )
    list_float: List[float] = Field(
        ...,
        title="List floats",
        description="List of floats.",
        examples=[[0.2, 0.5]],
    )
    list_int: List[float] = Field(
        ...,
        title="List ints",
        description="List of integers.",
        examples=[[1, 2, 3]],
    )
    list_date: List[date] = Field(
        ...,
        title="List dates",
        description="List of integers.",
        examples=[[date.fromisoformat("2025-01-01")]],
    )
    list_datetime: List[datetime] = Field(
        ...,
        title="List datetimes",
        description="List of datetimes.",
        examples=[[datetime.fromisoformat("2025-01-01T00:00:00+00:00")]],
    )
    list_bool: List[bool] = Field(
        ...,
        title="List booleans",
        description="List of booleans.",
        examples=[[True, False]],
    )
    list_enum: List[ExampleEnum] = Field(
        ...,
        title="List enums",
        description="List of booleans.",
        examples=[[ExampleEnum.FOO, ExampleEnum.BAR]],
    )


class ValidationRequest(ValidationBase):
    pass


class ValidationResponse(CamelCaseModel):
    ok: Optional[bool] = Field(
        None,
        title="OK",
        examples=[True],
    )


DEFINITION = DataProductDefinition(
    version="0.1.0",
    title="Validation testing",
    description="Definition for validating different kinds of fields",
    request=ValidationRequest,
    response=ValidationResponse,
    strict_validation=False,
)
