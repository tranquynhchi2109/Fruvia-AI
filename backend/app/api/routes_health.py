"""
Health and readiness check endpoints.
"""

from __future__ import annotations

import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.ml.classifier import FruitClassifier, get_fruit_classifier
from app.ml.image_encoder import ImageEncoder, get_image_encoder
from app.repositories.qdrant_repository import QdrantRepository, get_qdrant_repository

router = APIRouter(tags=["health"])

CACHE_TTL_SEC = 5.0
_health_cache: dict[str, Any] | None = None
_last_health_check_time: float = 0.0


class ClassificationHealthInfo(BaseModel):
    """Detailed health status for fruit classification engine."""

    status: str = Field(..., description="Classification readiness: ready | degraded | unavailable")
    model_loaded: bool = Field(..., description="Whether classification model engine is loaded")
    inference_method: str = Field(..., description="Method used: convnext_tiny | dinov2_qdrant_knn | unavailable")
    artifact_path: str | None = Field(default=None, description="Resolved artifact path if present")
    fallback: bool = Field(..., description="Whether fallback engine is active")


class HealthResponse(BaseModel):
    """Response schema for the health endpoint."""

    status: str = Field(..., description="Service status: ok | degraded | unavailable")
    model_loaded: bool = Field(..., description="Whether the image encoder model is loaded")
    qdrant_connected: bool = Field(..., description="Whether Qdrant Cloud is reachable")
    collection_available: bool = Field(
        ..., description="Whether the Qdrant collection is available"
    )
    classification: ClassificationHealthInfo = Field(
        ..., description="Fruit classifier health metadata"
    )
    version: str = Field(..., description="Application version")


@router.get("/health", response_model=HealthResponse)
async def health_check(
    encoder: Annotated[ImageEncoder, Depends(get_image_encoder)],
    repo: Annotated[QdrantRepository, Depends(get_qdrant_repository)],
    classifier: Annotated[FruitClassifier, Depends(get_fruit_classifier)],
) -> HealthResponse:
    """
    Service health check.

    Returns cached health status (TTL 5s) to avoid unnecessary Qdrant load.
    Combines Qdrant connection, collection availability, and classifier status.
    """
    global _health_cache, _last_health_check_time
    now = time.monotonic()

    if _health_cache is not None and (now - _last_health_check_time) < CACHE_TTL_SEC:
        return HealthResponse(**_health_cache)

    settings = get_settings()
    model_loaded = encoder.is_loaded

    # Single Qdrant health check call
    qdrant_connected, collection_available = repo.get_health_status()

    # Classifier status
    clf_audit = classifier.get_audit_info()
    clf_status = "ready"
    if classifier.model_source == "retrieval_knn_fallback":
        clf_status = "degraded"
    elif classifier.model_source == "unavailable":
        clf_status = "unavailable"

    classification_info = ClassificationHealthInfo(
        status=clf_status,
        model_loaded=classifier.is_loaded,
        inference_method=clf_audit["architecture"] if classifier.model_source == "trained_model" else "dinov2_qdrant_knn",
        artifact_path=clf_audit["artifact_path"],
        fallback=classifier.is_fallback,
    )

    if not (qdrant_connected and collection_available):
        overall_status = "unavailable"
    elif clf_status == "degraded" or not model_loaded:
        overall_status = "degraded"
    elif clf_status == "unavailable":
        overall_status = "degraded"
    else:
        overall_status = "ok"

    result_data = {
        "status": overall_status,
        "model_loaded": model_loaded,
        "qdrant_connected": qdrant_connected,
        "collection_available": collection_available,
        "classification": classification_info.model_dump(),
        "version": settings.app_version,
    }

    _health_cache = result_data
    _last_health_check_time = now

    return HealthResponse(**result_data)


@router.get("/ready")
async def readiness_check(
    encoder: Annotated[ImageEncoder, Depends(get_image_encoder)],
    repo: Annotated[QdrantRepository, Depends(get_qdrant_repository)],
    classifier: Annotated[FruitClassifier, Depends(get_fruit_classifier)],
) -> JSONResponse:
    """Readiness probe endpoint for Kubernetes / Docker container health checks."""
    qdrant_ok, coll_ok = repo.get_health_status()
    clf_ready = classifier.is_loaded and classifier.model_source != "unavailable"

    if encoder.is_loaded and qdrant_ok and coll_ok and clf_ready:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ready"},
        )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready"},
    )
