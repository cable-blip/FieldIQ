"""Validation for explicit external-source to FieldIQ CSV column mappings."""

from backend.app.schemas.dataset import (
    SourceColumnMappingIssue,
    SourceColumnMappingReport,
    SourceColumnMappingRequest,
)
from backend.app.services.dataset_validation import (
    OPTIONAL_DELIVERY_COLUMNS,
    REQUIRED_DELIVERY_COLUMNS,
)


CANONICAL_DELIVERY_COLUMNS = REQUIRED_DELIVERY_COLUMNS | frozenset(
    OPTIONAL_DELIVERY_COLUMNS
)


def validate_source_column_mapping(
    request: SourceColumnMappingRequest,
) -> SourceColumnMappingReport:
    """Validate mapping metadata without reading, transforming, or storing rows."""

    issues: list[SourceColumnMappingIssue] = []
    headers = request.source_headers
    header_set = set(headers)
    duplicate_headers = sorted(
        {header for header in headers if headers.count(header) > 1}
    )
    for header in headers:
        if not header.strip():
            issues.append(
                _issue(
                    source_field=header,
                    code="blank_source_header",
                    message="Source column names must not be blank.",
                )
            )
    for header in duplicate_headers:
        issues.append(
            _issue(
                source_field=header,
                code="duplicate_source_header",
                message=f"Source column '{header}' appears more than once.",
            )
        )

    mapping = request.column_mapping
    unknown_canonical_columns = sorted(set(mapping) - CANONICAL_DELIVERY_COLUMNS)
    for canonical_field in unknown_canonical_columns:
        issues.append(
            _issue(
                canonical_field=canonical_field,
                code="unknown_canonical_field",
                message="Field is not part of the FieldIQ delivery CSV contract.",
            )
        )

    for canonical_field in sorted(REQUIRED_DELIVERY_COLUMNS - set(mapping)):
        issues.append(
            _issue(
                canonical_field=canonical_field,
                code="missing_required_mapping",
                message="A source column must be mapped for this required field.",
            )
        )

    mapped_source_fields = list(mapping.values())
    duplicate_mapped_sources = sorted(
        {
            source_field
            for source_field in mapped_source_fields
            if mapped_source_fields.count(source_field) > 1
        }
    )
    for source_field in duplicate_mapped_sources:
        issues.append(
            _issue(
                source_field=source_field,
                code="source_column_mapped_multiple_times",
                message="A source column may map to only one canonical field.",
            )
        )

    for canonical_field, source_field in mapping.items():
        if not source_field.strip():
            issues.append(
                _issue(
                    canonical_field=canonical_field,
                    source_field=source_field,
                    code="blank_mapping_target",
                    message="A mapped source column name must not be blank.",
                )
            )
        elif source_field not in header_set:
            issues.append(
                _issue(
                    canonical_field=canonical_field,
                    source_field=source_field,
                    code="mapped_source_column_missing",
                    message="Mapped source column is not listed in source_headers.",
                )
            )

    return SourceColumnMappingReport(
        mapping_status="valid" if not issues else "invalid",
        mapped_columns=mapping,
        unmapped_source_columns=sorted(header_set - set(mapped_source_fields)),
        issues=issues,
    )


def _issue(
    *,
    canonical_field: str | None = None,
    source_field: str | None = None,
    code: str,
    message: str,
) -> SourceColumnMappingIssue:
    return SourceColumnMappingIssue(
        canonical_field=canonical_field,
        source_field=source_field,
        code=code,
        message=message,
    )
