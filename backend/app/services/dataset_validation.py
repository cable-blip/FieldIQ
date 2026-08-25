"""Validation for FieldIQ's canonical, delivery-level CSV contract."""

import csv
import io
from collections.abc import Iterable

from backend.app.schemas.dataset import (
    DELIVERY_CSV_SCHEMA_VERSION,
    DatasetMetadata,
    DatasetFieldAvailability,
    DatasetQualitySummary,
    DatasetValidationIssue,
    DatasetValidationReport,
)


REQUIRED_DELIVERY_COLUMNS = frozenset(
    {
        "match_id",
        "innings",
        "delivery_number",
        "batter_name",
        "bowler_name",
        "runs_batter",
        "runs_extras",
        "runs_total",
        "is_wicket",
    }
)

OPTIONAL_DELIVERY_COLUMNS = (
    "match_format",
    "batting_team",
    "bowling_team",
    "venue",
    "match_date",
    "non_striker_name",
    "wicket_type",
    "dismissed_batter",
    "delivery_line",
    "delivery_length",
    "release_speed_kph",
    "pitch_coordinates_x",
    "pitch_coordinates_y",
    "shot_coordinates_x",
    "shot_coordinates_y",
    "field_placement_id",
    "fielder_outcome",
)


def validate_delivery_csv(
    payload: bytes,
    metadata: DatasetMetadata,
) -> DatasetValidationReport:
    """Validate a CSV without storing it or filling in absent cricket data."""

    issues: list[DatasetValidationIssue] = []
    if metadata.schema_version != DELIVERY_CSV_SCHEMA_VERSION:
        issues.append(
            DatasetValidationIssue(
                field="schema_version",
                code="unsupported_schema_version",
                message=(
                    "Expected schema version "
                    f"'{DELIVERY_CSV_SCHEMA_VERSION}'."
                ),
            )
        )

    try:
        csv_text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        issues.append(
            DatasetValidationIssue(
                code="invalid_encoding",
                message="CSV must use UTF-8 encoding.",
            )
        )
        return _report(metadata, 0, 0, 0, issues)

    if not csv_text.strip():
        issues.append(
            DatasetValidationIssue(
                code="empty_file",
                message="CSV must contain a header row and at least one delivery.",
            )
        )
        return _report(metadata, 0, 0, 0, issues)

    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = reader.fieldnames
    if not fieldnames:
        issues.append(
            DatasetValidationIssue(
                code="missing_header",
                message="CSV must include a header row.",
            )
        )
        return _report(metadata, 0, 0, 0, issues)

    headers = [header or "" for header in fieldnames]
    missing_columns = sorted(REQUIRED_DELIVERY_COLUMNS - set(headers))
    duplicate_columns = sorted(
        {header for header in headers if header and headers.count(header) > 1}
    )
    if "" in headers:
        issues.append(
            DatasetValidationIssue(
                code="blank_header",
                message="CSV column names must not be blank.",
            )
        )
    for column in missing_columns:
        issues.append(
            DatasetValidationIssue(
                field=column,
                code="missing_required_column",
                message=f"Required column '{column}' is missing.",
            )
        )
    for column in duplicate_columns:
        issues.append(
            DatasetValidationIssue(
                field=column,
                code="duplicate_column",
                message=f"Column '{column}' appears more than once.",
            )
        )
    if missing_columns or duplicate_columns or "" in headers:
        return _report(metadata, 0, 0, 0, issues, headers=headers)

    total_rows = 0
    valid_rows = 0
    invalid_rows = 0
    delivery_keys: set[tuple[str, str, str]] = set()
    optional_value_counts = {column: 0 for column in OPTIONAL_DELIVERY_COLUMNS}
    for row_number, row in enumerate(reader, start=2):
        if row is None or not any(
            value and value.strip() for key, value in row.items() if key is not None
        ):
            continue
        total_rows += 1
        for column in OPTIONAL_DELIVERY_COLUMNS:
            if (row.get(column) or "").strip():
                optional_value_counts[column] += 1
        row_issues = _validate_delivery_row(row, row_number, delivery_keys)
        issues.extend(row_issues)
        if row_issues:
            invalid_rows += 1
        else:
            valid_rows += 1

    if total_rows == 0:
        issues.append(
            DatasetValidationIssue(
                code="empty_dataset",
                message="CSV must contain at least one delivery row.",
            )
        )

    return _report(
        metadata,
        total_rows,
        valid_rows,
        invalid_rows,
        issues,
        headers=headers,
        optional_value_counts=optional_value_counts,
    )


def _validate_delivery_row(
    row: dict[str | None, str | None],
    row_number: int,
    delivery_keys: set[tuple[str, str, str]],
) -> list[DatasetValidationIssue]:
    issues: list[DatasetValidationIssue] = []
    if row.get(None):
        issues.append(
            _issue(row_number, None, "unexpected_column_value", "Row has more values than headers.")
        )

    required_text = ("match_id", "batter_name", "bowler_name")
    values: dict[str, str] = {}
    for column in required_text:
        value = (row.get(column) or "").strip()
        values[column] = value
        if not value:
            issues.append(_issue(row_number, column, "required_value_missing", "Value is required."))

    innings = _non_negative_integer(row, "innings", row_number, issues, minimum=1)
    delivery_number = _non_negative_integer(
        row, "delivery_number", row_number, issues, minimum=1
    )
    runs_batter = _non_negative_integer(row, "runs_batter", row_number, issues)
    runs_extras = _non_negative_integer(row, "runs_extras", row_number, issues)
    runs_total = _non_negative_integer(row, "runs_total", row_number, issues)

    wicket_value = (row.get("is_wicket") or "").strip().lower()
    if wicket_value not in {"true", "false"}:
        issues.append(
            _issue(
                row_number,
                "is_wicket",
                "invalid_boolean",
                "Use 'true' or 'false'.",
            )
        )

    if None not in (runs_batter, runs_extras, runs_total) and runs_total != runs_batter + runs_extras:
        issues.append(
            _issue(
                row_number,
                "runs_total",
                "inconsistent_runs",
                "runs_total must equal runs_batter plus runs_extras.",
            )
        )

    if values["match_id"] and innings is not None and delivery_number is not None:
        key = (values["match_id"], str(innings), str(delivery_number))
        if key in delivery_keys:
            issues.append(
                _issue(
                    row_number,
                    "delivery_number",
                    "duplicate_delivery",
                    "match_id, innings, and delivery_number must be unique together.",
                )
            )
        else:
            delivery_keys.add(key)

    return issues


def _non_negative_integer(
    row: dict[str | None, str | None],
    column: str,
    row_number: int,
    issues: list[DatasetValidationIssue],
    *,
    minimum: int = 0,
) -> int | None:
    raw_value = (row.get(column) or "").strip()
    try:
        value = int(raw_value)
    except ValueError:
        issues.append(
            _issue(row_number, column, "invalid_integer", f"Use an integer greater than or equal to {minimum}.")
        )
        return None
    if value < minimum:
        issues.append(
            _issue(row_number, column, "integer_below_minimum", f"Use an integer greater than or equal to {minimum}.")
        )
        return None
    return value


def _issue(
    row_number: int,
    field: str | None,
    code: str,
    message: str,
) -> DatasetValidationIssue:
    return DatasetValidationIssue(
        row_number=row_number,
        field=field,
        code=code,
        message=message,
    )


def _report(
    metadata: DatasetMetadata,
    total_rows: int,
    valid_rows: int,
    invalid_rows: int,
    issues: Iterable[DatasetValidationIssue],
    *,
    headers: list[str] | None = None,
    optional_value_counts: dict[str, int] | None = None,
) -> DatasetValidationReport:
    issue_list = list(issues)
    return DatasetValidationReport(
        metadata=metadata,
        validation_status="valid" if not issue_list else "invalid",
        quality=DatasetQualitySummary(
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            valid_row_rate=valid_rows / total_rows if total_rows else 0,
        ),
        optional_field_availability=_optional_field_availability(
            headers or [], optional_value_counts or {}, total_rows
        ),
        issues=issue_list,
    )


def _optional_field_availability(
    headers: list[str],
    optional_value_counts: dict[str, int],
    total_rows: int,
) -> list[DatasetFieldAvailability]:
    header_set = set(headers)
    return [
        DatasetFieldAvailability(
            field=column,
            column_present=column in header_set,
            non_empty_values=optional_value_counts.get(column, 0),
            value_coverage_rate=(
                optional_value_counts.get(column, 0) / total_rows
                if total_rows
                else 0
            ),
        )
        for column in OPTIONAL_DELIVERY_COLUMNS
    ]
