from typing import Literal

from pydantic import BaseModel, Field


DELIVERY_CSV_SCHEMA_VERSION = "fieldiq.delivery-csv.v1"


class DatasetMetadata(BaseModel):
    """Traceability information supplied with a dataset validation request."""

    source_name: str = Field(min_length=1, max_length=200)
    dataset_version: str = Field(min_length=1, max_length=100)
    schema_version: str = Field(min_length=1, max_length=100)


class DatasetValidationIssue(BaseModel):
    row_number: int | None = Field(default=None, ge=1)
    field: str | None = None
    code: str
    message: str


class DatasetQualitySummary(BaseModel):
    total_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    invalid_rows: int = Field(ge=0)
    valid_row_rate: float = Field(ge=0, le=1)


class DatasetFieldAvailability(BaseModel):
    """Observed source coverage for one optional canonical field."""

    field: str
    column_present: bool
    non_empty_values: int = Field(ge=0)
    value_coverage_rate: float = Field(ge=0, le=1)


class SourceColumnMappingRequest(BaseModel):
    """An explicit, source-specific mapping into the FieldIQ CSV contract."""

    source_headers: list[str] = Field(min_length=1)
    column_mapping: dict[str, str] = Field(min_length=1)


class SourceColumnMappingIssue(BaseModel):
    canonical_field: str | None = None
    source_field: str | None = None
    code: str
    message: str


class SourceColumnMappingReport(BaseModel):
    mapping_status: Literal["valid", "invalid"]
    mapped_columns: dict[str, str]
    unmapped_source_columns: list[str]
    issues: list[SourceColumnMappingIssue]


class DatasetValidationReport(BaseModel):
    """A validation-only result; the submitted CSV is never persisted."""

    metadata: DatasetMetadata
    validation_status: Literal["valid", "invalid"]
    quality: DatasetQualitySummary
    optional_field_availability: list[DatasetFieldAvailability] = Field(
        default_factory=list
    )
    issues: list[DatasetValidationIssue]
