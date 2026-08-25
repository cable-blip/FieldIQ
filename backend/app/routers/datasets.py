from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status

from backend.app.schemas.dataset import (
    DELIVERY_CSV_SCHEMA_VERSION,
    DatasetMetadata,
    DatasetValidationReport,
    SourceColumnMappingReport,
    SourceColumnMappingRequest,
)
from backend.app.services.column_mapping_validation import (
    validate_source_column_mapping,
)
from backend.app.services.dataset_validation import validate_delivery_csv

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])


@router.post(
    "/column-mappings/validate",
    response_model=SourceColumnMappingReport,
    status_code=status.HTTP_200_OK,
)
def validate_column_mapping(
    request: SourceColumnMappingRequest,
) -> SourceColumnMappingReport:
    """Check an explicit external-source header mapping before any row conversion."""

    return validate_source_column_mapping(request)


@router.post(
    "/validate",
    response_model=DatasetValidationReport,
    status_code=status.HTTP_200_OK,
)
async def validate_dataset_csv(
    request: Request,
    source_name: Annotated[str, Query(min_length=1, max_length=200)],
    dataset_version: Annotated[str, Query(min_length=1, max_length=100)],
    schema_version: Annotated[
        str, Query(min_length=1, max_length=100)
    ] = DELIVERY_CSV_SCHEMA_VERSION,
) -> DatasetValidationReport:
    """Validate a UTF-8 CSV sent as a `text/csv` request body; do not store it."""

    content_type = request.headers.get("content-type", "").split(";", maxsplit=1)[0]
    if content_type != "text/csv":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type must be text/csv.",
        )

    return validate_delivery_csv(
        await request.body(),
        DatasetMetadata(
            source_name=source_name,
            dataset_version=dataset_version,
            schema_version=schema_version,
        ),
    )
