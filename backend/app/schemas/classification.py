"""
Pydantic schemas for classification endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    """A single class prediction with confidence."""

    class_name: str = Field(..., description="Predicted fruit class name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0–1)")


class ClassificationResponse(BaseModel):
    """Response body for POST /api/classify."""

    prediction: PredictionItem = Field(..., description="Top prediction")
    top_predictions: list[PredictionItem] = Field(
        ..., description="Top-K predictions ordered by confidence"
    )
    accepted: bool = Field(
        ..., description="Whether the prediction confidence exceeds the threshold"
    )
    threshold: float = Field(..., description="Confidence threshold used")
    message: str = Field(default="", description="Human-readable status message")
    processing_time_ms: float = Field(..., description="Inference time in milliseconds")

    # Engine & Metadata
    inference_method: str = Field(
        default="convnext_tiny",
        description="Model architecture or method used (e.g., convnext_tiny, dinov2_qdrant_knn)",
    )
    model_name: str = Field(default="convnext_tiny", description="Identifier of the model")
    model_source: str = Field(
        default="trained_artifact",
        description="Source of prediction: trained_artifact | retrieval_knn_fallback | unavailable",
    )
    model_ready: bool = Field(default=True, description="Whether classification model is ready")
    is_fallback: bool = Field(
        default=False, description="Whether prediction used a fallback mechanism"
    )


class ClassificationErrorResponse(BaseModel):
    """Error response for classification failures."""

    error: bool = True
    error_code: str
    message: str
