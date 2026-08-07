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
    and decision threshold checks (Softmax probability vs kNN hybrid score).
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

        # 2. Run inference via classifier engine
        result_data = self.classifier.predict(pil_image, top_k=top_k)
        raw_predictions = result_data["predictions"]

        # 3. Format top predictions
        top_predictions = [
            PredictionItem(class_name=name, confidence=conf)
            for name, conf in raw_predictions
        ]

        top_1 = top_predictions[0] if top_predictions else PredictionItem(class_name="unknown", confidence=0.0)
        score_type = result_data.get("score_type", "softmax_probability")
        method = result_data.get("inference_method", "convnext_tiny")
        is_fallback = result_data.get("is_fallback", False)

        # 4. Evaluate decision threshold according to score_type semantics
        if score_type == "softmax_probability":
            threshold_used = self.settings.classification_threshold
            accepted = top_1.confidence >= threshold_used
            if accepted:
                message = f"Prediction '{top_1.class_name}' accepted with {top_1.confidence * 100:.1f}% confidence."
            else:
                message = (
                    f"Prediction '{top_1.class_name}' ({top_1.confidence * 100:.1f}%) "
                    f"is below confidence threshold ({threshold_used * 100:.0f}%)."
                )
        else:
            # kNN Fallback decision rules
            threshold_used = self.settings.knn_min_top_similarity
            winning_top_sim = result_data.get("winning_top_sim", 0.0)
            winning_margin = result_data.get("winning_margin", 0.0)
            winning_support = result_data.get("winning_support", 0)

            accepted = (
                winning_top_sim >= self.settings.knn_min_top_similarity
                and winning_margin >= self.settings.knn_min_margin
                and winning_support >= self.settings.knn_min_support
            )

            agreement = result_data.get("neighbor_agreement", "0/20")
            if accepted:
                message = (
                    f"kNN Match '{top_1.class_name}' accepted (Score: {top_1.confidence:.2f}, "
                    f"Neighbor Agreement: {agreement}, Top Sim: {winning_top_sim:.2f})."
                )
            else:
                message = (
                    f"kNN Match '{top_1.class_name}' low confidence (Score: {top_1.confidence:.2f}, "
                    f"Agreement: {agreement}, Top Sim: {winning_top_sim:.2f} < {threshold_used:.2f})."
                )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        logger.info(
            "Classification completed for '%s' in %.2f ms via %s (%s). Top prediction: %s (%.2f)",
            filename,
            elapsed_ms,
            method,
            score_type,
            top_1.class_name,
            top_1.confidence,
        )

        return ClassificationResponse(
            prediction=top_1,
            top_predictions=top_predictions,
            accepted=accepted,
            threshold=threshold_used,
            message=message,
            processing_time_ms=elapsed_ms,
            score_type=score_type,
            inference_method=method,
            model_name=result_data.get("model_name", method),
            model_source=result_data.get("model_source", "trained_artifact"),
            model_ready=self.classifier.is_loaded,
            is_fallback=is_fallback,
            neighbor_agreement=result_data.get("neighbor_agreement"),
            top_similarity=result_data.get("top_similarity"),
        )


def get_classification_service() -> ClassificationService:
    """Return ClassificationService instance."""
    return ClassificationService()
