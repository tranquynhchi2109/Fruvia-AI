"""
Classification API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.exceptions import ImageValidationError, ModelNotLoadedError
from app.schemas.classification import ClassificationResponse
from app.services.classification_service import ClassificationService, get_classification_service

router = APIRouter(tags=["classification"])


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify fruit image",
    description="Upload a fruit image and get top-K predictions with confidence scores.",
)
async def classify_image(
    file: Annotated[UploadFile, File(description="Fruit image file (JPG, PNG, WEBP, max 10MB)")],
    top_k: Annotated[int, Form(description="Number of top predictions to return (1-10)")] = 3,
    service: Annotated[ClassificationService, Depends(get_classification_service)] = None,
) -> ClassificationResponse:
    """Classify fruit image endpoint."""
    if not file.filename:
        raise ImageValidationError(
            message="No filename provided.",
            detail="The uploaded file must have a valid filename.",
        )

    if top_k < 1 or top_k > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="top_k must be between 1 and 10.",
        )

    if not service.classifier.is_loaded or service.classifier.model_source == "unavailable":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fruit classification model is not available.",
        )

    file_bytes = await file.read()

    try:
        response = await run_in_threadpool(
            service.classify_image,
            file_bytes=file_bytes,
            filename=file.filename,
            top_k=top_k,
            content_type=file.content_type,
        )
        return response
    except ModelNotLoadedError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message,
        ) from e
