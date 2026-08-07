"""
Regression and debugging unit test suite for kNN classification decision logic,
confusion scenarios (Guava vs Pomegranate, Pear vs Guava, Apple vs Pomegranate),
and separate threshold evaluation.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.ml.classifier import FruitClassifier
from app.schemas.classification import ClassificationResponse
from app.services.classification_service import ClassificationService


@pytest.fixture
def dummy_image() -> Image.Image:
    return Image.new("RGB", (224, 224), color=(0, 200, 50))  # Green image simulating a fruit


class TestKNNConfusionAndDecisionLogic:
    """Test kNN hybrid scoring and separate acceptance thresholds."""

    def test_guava_winning_with_high_neighbor_agreement(self, dummy_image: Image.Image):
        """Verify clear Guava image with strong neighbor support passes kNN acceptance."""
        classifier = FruitClassifier()
        classifier.model_source = "retrieval_knn_fallback"
        classifier.is_loaded = True
        classifier.is_fallback = True

        hits = []
        # 14 Guava hits (high similarity)
        for i in range(14):
            m = MagicMock()
            m.canonical_class = "guava"
            m.similarity = 0.82 - (i * 0.01)
            hits.append(m)

        # 6 Pomegranate hits (lower similarity)
        for i in range(6):
            m = MagicMock()
            m.canonical_class = "pomegranate"
            m.similarity = 0.50 - (i * 0.01)
            hits.append(m)

        mock_qdrant = MagicMock()
        mock_qdrant.query_similar.return_value = hits

        mock_encoder = MagicMock()
        mock_encoder.is_loaded = True
        mock_encoder.encode_image.return_value = [0.05] * 768

        with patch("app.ml.image_encoder.get_image_encoder", return_value=mock_encoder), \
             patch("app.repositories.qdrant_repository.get_qdrant_repository", return_value=mock_qdrant):

            result = classifier.predict(dummy_image, top_k=3)

            assert result["inference_method"] == "dinov2_qdrant_knn"
            assert result["score_type"] == "knn_vote"
            assert result["is_fallback"] is True
            assert result["neighbor_agreement"] == "14/20"
            assert result["top_similarity"] == 0.82

            top_class, top_score = result["predictions"][0]
            assert top_class == "guava"
            assert top_score > 0.60

            # Test via ClassificationService to check acceptance logic
            with patch("app.services.classification_service.validate_upload", return_value=(dummy_image, "image/png")):
                service = ClassificationService(classifier=classifier)
                resp = service.classify_image(b"fake_bytes", "guava_test.png", top_k=3)

                assert isinstance(resp, ClassificationResponse)
                assert resp.prediction.class_name == "guava"
                assert resp.accepted is True  # Meets top_sim (0.82 >= 0.45), margin, & support (14 >= 3)
                assert resp.score_type == "knn_vote"
                assert resp.neighbor_agreement == "14/20"

    def test_low_similarity_knn_rejected(self, dummy_image: Image.Image):
        """Verify ambiguous image with low similarity fails kNN acceptance."""
        classifier = FruitClassifier()
        classifier.model_source = "retrieval_knn_fallback"
        classifier.is_loaded = True
        classifier.is_fallback = True

        hits = []
        for cls in ["apple", "pear", "mango"]:
            m = MagicMock()
            m.canonical_class = cls
            m.similarity = 0.30
            hits.append(m)

        mock_qdrant = MagicMock()
        mock_qdrant.query_similar.return_value = hits

        mock_encoder = MagicMock()
        mock_encoder.is_loaded = True
        mock_encoder.encode_image.return_value = [0.05] * 768

        with patch("app.ml.image_encoder.get_image_encoder", return_value=mock_encoder), \
             patch("app.repositories.qdrant_repository.get_qdrant_repository", return_value=mock_qdrant):

            with patch("app.services.classification_service.validate_upload", return_value=(dummy_image, "image/png")):
                service = ClassificationService(classifier=classifier)
                resp = service.classify_image(b"fake_bytes", "ambiguous.png", top_k=3)

                assert resp.accepted is False  # Fails top_sim (0.30 < 0.45)
                assert "low confidence" in resp.message.lower()

    def test_trained_classifier_uses_softmax_probability_and_threshold(self, dummy_image: Image.Image):
        """Verify trained neural model strictly uses Softmax probability and 0.65 threshold."""
        classifier = FruitClassifier()
        classifier.model_source = "trained_model"
        classifier.is_loaded = True
        classifier.is_fallback = False

        mock_model_output = {
            "predictions": [("guava", 0.92), ("pomegranate", 0.05)],
            "score_type": "softmax_probability",
            "inference_method": "convnext_tiny",
            "model_name": "convnext_tiny",
            "model_source": "trained_artifact",
            "is_fallback": False,
        }

        with patch.object(classifier, "predict", return_value=mock_model_output), \
             patch("app.services.classification_service.validate_upload", return_value=(dummy_image, "image/png")):

            service = ClassificationService(classifier=classifier)
            resp = service.classify_image(b"fake_bytes", "guava_nn.png", top_k=2)

            assert resp.score_type == "softmax_probability"
            assert resp.accepted is True  # 0.92 >= 0.65
            assert resp.is_fallback is False
            assert resp.prediction.class_name == "guava"
            assert resp.prediction.confidence == 0.92
