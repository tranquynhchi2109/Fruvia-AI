"""
Pydantic schemas for classification endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionItem(BaseModel):
    """A single class prediction with confidence / score."""

    class_name: str = Field(..., description="Predicted fruit class name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction score or confidence (0–1)")


class ClassificationResponse(BaseModel):
    """Response body for POST /api/classify."""

    prediction: PredictionItem = Field(..., description="Top prediction")
    top_predictions: list[PredictionItem] = Field(
        ..., description="Top-K predictions ordered by confidence"
    )
    accepted: bool = Field(
        ..., description="Whether the prediction satisfies the decision threshold"
    )
    threshold: float = Field(..., description="Threshold value used for acceptance decision")
    message: str = Field(default="", description="Human-readable status message")
    processing_time_ms: float = Field(..., description="Inference time in milliseconds")

    # Engine & Metadata
    score_type: str = Field(
        default="softmax_probability",
        description="Type of score returned: softmax_probability | knn_vote",
    )
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

    # Detailed kNN Metrics (Present when is_fallback == True)
    neighbor_agreement: str | None = Field(
        default=None, description="Neighbor support ratio (e.g., '14/20')"
    )
    top_similarity: float | None = Field(
        default=None, description="Cosine similarity score of top nearest neighbor (0-1)"
    )


class ClassificationErrorResponse(BaseModel):
    """Error response for classification failures."""

    error: bool = True
    error_code: str
    message: str
