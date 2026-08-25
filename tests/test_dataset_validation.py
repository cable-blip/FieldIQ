from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.dataset import (
    DELIVERY_CSV_SCHEMA_VERSION,
    DatasetMetadata,
    SourceColumnMappingRequest,
)
from backend.app.services.column_mapping_validation import validate_source_column_mapping
from backend.app.services.dataset_validation import validate_delivery_csv

client = TestClient(app)

VALID_CSV = b"""match_id,innings,delivery_number,batter_name,bowler_name,runs_batter,runs_extras,runs_total,is_wicket
fixture-match-001,1,1,batter_a,bowler_a,0,0,0,false
fixture-match-001,1,2,batter_a,bowler_a,4,0,4,false
"""


def _metadata() -> DatasetMetadata:
    return DatasetMetadata(
        source_name="test-fixture",
        dataset_version="test-v1",
        schema_version=DELIVERY_CSV_SCHEMA_VERSION,
    )


def test_validates_a_canonical_delivery_csv_via_api() -> None:
    response = client.post(
        "/api/v1/datasets/validate",
        params={"source_name": "test-fixture", "dataset_version": "test-v1"},
        content=VALID_CSV,
        headers={"content-type": "text/csv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "valid"
    assert body["metadata"] == {
        "source_name": "test-fixture",
        "dataset_version": "test-v1",
        "schema_version": DELIVERY_CSV_SCHEMA_VERSION,
    }
    assert body["quality"] == {
        "total_rows": 2,
        "valid_rows": 2,
        "invalid_rows": 0,
        "valid_row_rate": 1.0,
    }
    assert body["issues"] == []


def test_reports_invalid_delivery_values_without_changing_them() -> None:
    invalid_csv = VALID_CSV.replace(b",4,0,4,false", b",4,0,5,false")

    report = validate_delivery_csv(invalid_csv, _metadata())

    assert report.validation_status == "invalid"
    assert report.quality.total_rows == 2
    assert report.quality.valid_rows == 1
    assert report.quality.invalid_rows == 1
    assert any(issue.code == "inconsistent_runs" for issue in report.issues)


def test_rejects_missing_required_column_before_reading_rows() -> None:
    csv_without_bowler = VALID_CSV.replace(b"bowler_name,", b"")

    report = validate_delivery_csv(csv_without_bowler, _metadata())

    assert report.validation_status == "invalid"
    assert report.quality.total_rows == 0
    assert [(issue.field, issue.code) for issue in report.issues] == [
        ("bowler_name", "missing_required_column")
    ]


def test_rejects_duplicate_delivery_identifiers() -> None:
    duplicate_delivery = VALID_CSV.replace(b",1,2,", b",1,1,")

    report = validate_delivery_csv(duplicate_delivery, _metadata())

    assert report.validation_status == "invalid"
    assert report.quality.invalid_rows == 1
    assert any(issue.code == "duplicate_delivery" for issue in report.issues)


def test_rejects_unsupported_schema_version() -> None:
    report = validate_delivery_csv(
        VALID_CSV,
        DatasetMetadata(
            source_name="test-fixture",
            dataset_version="test-v1",
            schema_version="unsupported-v0",
        ),
    )

    assert report.validation_status == "invalid"
    assert any(issue.code == "unsupported_schema_version" for issue in report.issues)


def test_requires_csv_content_type() -> None:
    response = client.post(
        "/api/v1/datasets/validate",
        params={"source_name": "test-fixture", "dataset_version": "test-v1"},
        content=VALID_CSV,
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Content-Type must be text/csv."


def test_reports_observed_optional_field_coverage_without_inferring_values() -> None:
    csv_with_optional_fields = b"""match_id,innings,delivery_number,batter_name,bowler_name,runs_batter,runs_extras,runs_total,is_wicket,venue,delivery_line
fixture-match-001,1,1,batter_a,bowler_a,0,0,0,false,fixture-ground,
fixture-match-001,1,2,batter_a,bowler_a,4,0,4,false,fixture-ground,off_stump
"""

    report = validate_delivery_csv(csv_with_optional_fields, _metadata())
    coverage = {item.field: item for item in report.optional_field_availability}

    assert report.validation_status == "valid"
    assert coverage["venue"].column_present is True
    assert coverage["venue"].non_empty_values == 2
    assert coverage["venue"].value_coverage_rate == 1.0
    assert coverage["delivery_line"].column_present is True
    assert coverage["delivery_line"].non_empty_values == 1
    assert coverage["delivery_line"].value_coverage_rate == 0.5
    assert coverage["field_placement_id"].column_present is False
    assert coverage["field_placement_id"].non_empty_values == 0


def test_accepts_an_explicit_complete_source_column_mapping() -> None:
    source_headers = [
        "game",
        "innings_no",
        "sequence",
        "striker",
        "bowler",
        "batter_runs",
        "extra_runs",
        "total_runs",
        "wicket",
        "ground_name",
    ]
    mapping = {
        "match_id": "game",
        "innings": "innings_no",
        "delivery_number": "sequence",
        "batter_name": "striker",
        "bowler_name": "bowler",
        "runs_batter": "batter_runs",
        "runs_extras": "extra_runs",
        "runs_total": "total_runs",
        "is_wicket": "wicket",
        "venue": "ground_name",
    }

    report = validate_source_column_mapping(
        SourceColumnMappingRequest(
            source_headers=source_headers,
            column_mapping=mapping,
        )
    )

    assert report.mapping_status == "valid"
    assert report.mapped_columns == mapping
    assert report.unmapped_source_columns == []
    assert report.issues == []


def test_rejects_incomplete_or_ambiguous_source_column_mapping() -> None:
    report = validate_source_column_mapping(
        SourceColumnMappingRequest(
            source_headers=["game", "innings_no"],
            column_mapping={
                "match_id": "game",
                "innings": "game",
                "not_a_contract_field": "innings_no",
            },
        )
    )

    codes = {issue.code for issue in report.issues}
    assert report.mapping_status == "invalid"
    assert "missing_required_mapping" in codes
    assert "unknown_canonical_field" in codes
    assert "source_column_mapped_multiple_times" in codes


def test_validates_source_column_mapping_via_api() -> None:
    response = client.post(
        "/api/v1/datasets/column-mappings/validate",
        json={
            "source_headers": [
                "game",
                "innings_no",
                "sequence",
                "striker",
                "bowler",
                "batter_runs",
                "extra_runs",
                "total_runs",
                "wicket",
            ],
            "column_mapping": {
                "match_id": "game",
                "innings": "innings_no",
                "delivery_number": "sequence",
                "batter_name": "striker",
                "bowler_name": "bowler",
                "runs_batter": "batter_runs",
                "runs_extras": "extra_runs",
                "runs_total": "total_runs",
                "is_wicket": "wicket",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["mapping_status"] == "valid"
