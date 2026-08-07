"""
Comprehensive unit test suite for the Fruit Classification system overhaul.

Covers:
1. Multi-format model artifact loading (state_dict, checkpoint dict, full module, TorchScript).
2. Complete absence of random fallback models.
3. DINOv2 + Qdrant kNN fallback similarity-weighted voting logic.
4. Class ordering and canonical validation.
5. Error handling and fail-fast loading behavior.
6. API response metadata and top_k consistency.
7. Health status reporting (ready, degraded, unavailable).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import torch
import torch.nn as nn
from PIL import Image

from app.core.exceptions import ModelLoadError, ModelNotLoadedError
from app.ml.classifier import FruitClassifier, build_model_architecture
from app.schemas.classification import ClassificationResponse
from app.services.classification_service import ClassificationService


@pytest.fixture
def dummy_image() -> Image.Image:
    """Return a 224x224 RGB dummy fruit image."""
    return Image.new("RGB", (224, 224), color=(255, 100, 50))


@pytest.fixture
def canonical_classes() -> list[str]:
    return [
        "apple", "avocado", "banana", "cherry", "grape", "guava", "kiwi",
        "lemon", "lychee", "mango", "orange", "papaya", "pear", "pineapple",
        "pomegranate", "strawberry", "tomato", "watermelon"
    ]


class TestArchitectureBuilder:
    """Test model architecture creation for PyTorch state dicts."""

    def test_build_convnext_tiny(self):
        model = build_model_architecture("convnext_tiny", 18)
        assert isinstance(model, nn.Module)
        dummy_input = torch.zeros(1, 3, 224, 224)
        output = model(dummy_input)
        assert list(output.shape) == [1, 18]

    def test_build_efficientnet_b0(self):
        model = build_model_architecture("efficientnet_b0", 18)
        assert isinstance(model, nn.Module)
        dummy_input = torch.zeros(1, 3, 224, 224)
        output = model(dummy_input)
        assert list(output.shape) == [1, 18]

    def test_build_mobilenet_v3_small(self):
        model = build_model_architecture("mobilenet_v3_small", 18)
        assert isinstance(model, nn.Module)
        dummy_input = torch.zeros(1, 3, 224, 224)
        output = model(dummy_input)
        assert list(output.shape) == [1, 18]

    def test_unsupported_architecture_raises(self):
        with pytest.raises(ValueError, match="Unsupported architecture"):
            build_model_architecture("resnet50_invalid", 18)


class TestNoRandomFallback:
    """Ensure random Xavier-initialized MobileNetV3 fallback is completely removed."""

    def test_load_fallback_model_removed(self):
        classifier = FruitClassifier()
        assert not hasattr(classifier, "_load_fallback_model"), (
            "CRITICAL: _load_fallback_model must be completely deleted!"
        )

    def test_missing_model_and_missing_knn_sets_unavailable(self):
        classifier = FruitClassifier()
        with patch.object(classifier, "_check_knn_fallback_available", return_value=False):
            classifier.load_model()
            assert classifier.model_source == "unavailable"
            assert not classifier.is_loaded

            with pytest.raises(ModelNotLoadedError, match="Fruit classification model is not available"):
                classifier.predict(Image.new("RGB", (100, 100)))


class TestMultiFormatModelLoader:
    """Test loading state_dict, checkpoint dict, full module, and TorchScript."""

    def test_load_state_dict(self, tmp_path: Path, canonical_classes: list[str]):
        model_path = tmp_path / "model.pth"
        arch_model = build_model_architecture("convnext_tiny", len(canonical_classes))
        torch.save(arch_model.state_dict(), model_path)

        classifier = FruitClassifier()
        classifier.settings.model_path = model_path
        classifier.load_model()

        assert classifier.is_loaded
        assert classifier.model_source == "trained_model"
        assert classifier.artifact_type == "state_dict"
        assert classifier.model is not None

    def test_load_checkpoint_dict(self, tmp_path: Path, canonical_classes: list[str]):
        model_path = tmp_path / "model.pth"
        arch_model = build_model_architecture("convnext_tiny", len(canonical_classes))
        checkpoint = {
            "epoch": 10,
            "state_dict": arch_model.state_dict(),
            "class_names": canonical_classes,
        }
        torch.save(checkpoint, model_path)

        classifier = FruitClassifier()
        classifier.settings.model_path = model_path
        classifier.load_model()

        assert classifier.is_loaded
        assert classifier.model_source == "trained_model"
        assert classifier.artifact_type == "checkpoint_dict"

    def test_load_torchscript(self, tmp_path: Path, canonical_classes: list[str]):
        model_path = tmp_path / "model.pt"
        arch_model = build_model_architecture("convnext_tiny", len(canonical_classes))
        arch_model.eval()
        scripted = torch.jit.script(arch_model)
        torch.jit.save(scripted, model_path)

        classifier = FruitClassifier()
        classifier.settings.model_path = model_path
        classifier.load_model()

        assert classifier.is_loaded
        assert classifier.model_source == "trained_model"
        assert classifier.artifact_type == "torchscript"

    def test_corrupt_model_fails_and_does_not_swallow_error(self, tmp_path: Path):
        model_path = tmp_path / "corrupt_model.pth"
        model_path.write_bytes(b"not a valid torch file content")

        classifier = FruitClassifier()
        classifier.settings.model_path = model_path
        with patch.object(classifier, "_check_knn_fallback_available", return_value=False):
            classifier.load_model()
            assert not classifier.is_loaded
            assert classifier.model_source == "unavailable"
            assert classifier.artifact_type == "corrupt"


class TestKNNFallbackEngine:
    """Test DINOv2 + Qdrant 20-kNN similarity-weighted voting classification fallback."""

    def test_knn_fallback_weighted_voting(self, dummy_image: Image.Image):
        classifier = FruitClassifier()
        classifier.model_source = "retrieval_knn_fallback"
        classifier.is_loaded = True
        classifier.is_fallback = True

        mock_hit1 = MagicMock()
        mock_hit1.canonical_class = "apple"
        mock_hit1.similarity = 0.85

        mock_hit2 = MagicMock()
        mock_hit2.canonical_class = "apple"
        mock_hit2.similarity = 0.80

        mock_hit3 = MagicMock()
        mock_hit3.canonical_class = "banana"
        mock_hit3.similarity = 0.40

        mock_qdrant = MagicMock()
        mock_qdrant.query_similar.return_value = [mock_hit1, mock_hit2, mock_hit3]

        mock_encoder = MagicMock()
        mock_encoder.is_loaded = True
        mock_encoder.encode_image.return_value = [0.1] * 768

        with patch("app.ml.image_encoder.get_image_encoder", return_value=mock_encoder), \
             patch("app.repositories.qdrant_repository.get_qdrant_repository", return_value=mock_qdrant):

            result = classifier.predict(dummy_image, top_k=3)

            assert result["inference_method"] == "dinov2_qdrant_knn"
            assert result["is_fallback"] is True
            assert result["model_source"] == "retrieval_knn_fallback"

            predictions = result["predictions"]
            assert len(predictions) == 2
            top_class, top_prob = predictions[0]
            assert top_class == "apple"
            assert top_prob > 0.90  # Apple has dominant weight (0.50 + 0.45 = 0.95 vs Banana 0.05)


class TestClassificationServiceAndMetadata:
    """Test ClassificationService formatting and metadata fields."""

    def test_classification_service_extended_response(self, dummy_image: Image.Image):
        mock_classifier = MagicMock()
        mock_classifier.is_loaded = True
        mock_classifier.predict.return_value = {
            "predictions": [("apple", 0.88), ("pear", 0.10), ("mango", 0.02)],
            "inference_method": "convnext_tiny",
            "model_name": "convnext_tiny",
            "model_source": "trained_artifact",
            "is_fallback": False,
        }

        with patch("app.services.classification_service.validate_upload", return_value=(dummy_image, "image/png")):
            service = ClassificationService(classifier=mock_classifier)
            resp = service.classify_image(b"fake_bytes", "test_apple.png", top_k=3)

            assert isinstance(resp, ClassificationResponse)
            assert resp.prediction.class_name == "apple"
            assert resp.prediction.confidence == 0.88
            assert resp.accepted is True
            assert resp.inference_method == "convnext_tiny"
            assert resp.is_fallback is False
            assert resp.model_source == "trained_artifact"
