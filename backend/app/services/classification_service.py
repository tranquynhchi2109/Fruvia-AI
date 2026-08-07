"""
Business logic service for fruit classification.
"""

from __future__ import annotations

import time

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.ml.classifier import FruitClassifier, get_fruit_classifier
from app.schemas.classification import ClassificationResponse, PredictionItem
from app.utils.image_validation import validate_upload

logger = get_logger(__name__)


class ClassificationService:
    """
    Service orchestrating image validation, fruit classification inference,
    and threshold confidence check.
    """

    def __init__(
        self,
        classifier: FruitClassifier | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.classifier = classifier or get_fruit_classifier()
        self.settings = settings or get_settings()

    def classify_image(
        self,
        file_bytes: bytes,
        filename: str,
        top_k: int = 3,
        content_type: str | None = None,
    ) -> ClassificationResponse:
        """
        Process uploaded image bytes and predict fruit class with confidence scores.
        """
        start_time = time.perf_counter()

        logger.info(
            "Processing classification request for file '%s' (bytes=%d, top_k=%d)...",
            filename,
            len(file_bytes),
            top_k,
        )

        # 1. Validate image format, size, and integrity
        pil_image, _ = validate_upload(
            data=file_bytes,
            filename=filename,
            max_bytes=self.settings.max_upload_bytes,
            content_type=content_type,
        )

        # 2. Run inference
        raw_predictions = self.classifier.predict(pil_image, top_k=top_k)

        # 3. Format top predictions
        top_predictions = [
            PredictionItem(class_name=name, confidence=conf)
            for name, conf in raw_predictions
        ]

        top_1 = top_predictions[0] if top_predictions else PredictionItem(class_name="unknown", confidence=0.0)
        accepted = top_1.confidence >= self.settings.classification_threshold
        threshold = self.settings.classification_threshold

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        message = (
            f"Prediction '{top_1.class_name}' accepted with {top_1.confidence * 100:.1f}% confidence."
            if accepted
            else f"Prediction '{top_1.class_name}' ({top_1.confidence * 100:.1f}%) is below confidence threshold ({threshold * 100:.0f}%)."
        )

        logger.info(
            "Classification completed for '%s' in %.2f ms. Top prediction: %s (%.2f)",
            filename,
            elapsed_ms,
            top_1.class_name,
            top_1.confidence,
        )

        return ClassificationResponse(
            prediction=top_1,
            top_predictions=top_predictions,
            accepted=accepted,
            threshold=threshold,
            message=message,
            processing_time_ms=elapsed_ms,
        )


def get_classification_service() -> ClassificationService:
    """Return ClassificationService instance."""
    return ClassificationService()
