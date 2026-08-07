"""
Fruit classifier implementation for Fruvia AI.

Provides model loading and inference for fruit image classification.
Supports custom trained model loading (state_dict, checkpoint dict, TorchScript)
or fallback to DINOv2 + Qdrant kNN similarity-weighted classification.
NO random neural network fallback is ever used.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelLoadError, ModelNotLoadedError, PredictionError
from app.core.logging import get_logger
from app.ml.preprocessing import get_preprocessing_transforms, load_preprocessing_config
from app.utils.file_utils import load_yaml_config

logger = get_logger(__name__)

DEFAULT_PREPROCESSING_CONFIG = {
    "image_size": 224,
    "mean": [0.485, 0.456, 0.406],
    "std": [0.229, 0.224, 0.225],
    "interpolation": "bilinear",
    "color_mode": "RGB",
}


def build_model_architecture(architecture: str, num_classes: int) -> nn.Module:
    """Build PyTorch torchvision model architecture with custom classification head."""
    import torchvision.models as models

    arch_lower = architecture.lower().replace("-", "_")

    if "convnext" in arch_lower:
        model = models.convnext_tiny(weights=None)
        in_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(in_features, num_classes)
        return model

    if "efficientnet" in arch_lower:
        model = models.efficientnet_b0(weights=None)
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, num_classes)
        return model

    if "mobilenet" in arch_lower:
        model = models.mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, num_classes)
        return model

    raise ValueError(
        f"Unsupported architecture '{architecture}'. "
        f"Supported: convnext_tiny, efficientnet_b0, mobilenet_v3_small"
    )


class FruitClassifier:
    """
    Fruit classifier service.

    Hierarchical classification engine:
    1. Primary: Trained PyTorch classifier (TorchScript, StateDict, Full Model)
    2. Fallback: DINOv2 + Qdrant 20-kNN similarity-weighted voting
    3. Unavailable: Raises HTTP 503 error if neither engine is available.

    NO random weights fallback is ever used.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model: Any = None
        self.class_names: list[str] = []
        self.preprocessing_config: dict[str, Any] = DEFAULT_PREPROCESSING_CONFIG
        self.transforms: Any = None
        self.architecture: str = "convnext_tiny"
        self.artifact_type: str = "none"
        self.artifact_exists: bool = False
        self.artifact_path: Path | None = None
        self.model_source: str = "unavailable"  # "trained_model" | "retrieval_knn_fallback" | "unavailable"
        self.is_loaded: bool = False
        self.is_fallback: bool = False

    def load_model(self) -> None:
        """Load trained model weights or configure kNN fallback."""
        if self.is_loaded and self.model_source == "trained_model":
            logger.info("FruitClassifier trained model is already loaded.")
            return

        # 1. Always resolve canonical class list first
        self.class_names = self._load_canonical_class_names()

        # 2. Resolve preprocessing config
        prep_path = self.settings.resolved_preprocessing_config_path
        if prep_path.exists():
            try:
                self.preprocessing_config = load_preprocessing_config(prep_path)
                logger.info("Loaded preprocessing config from '%s'", prep_path)
            except Exception as e:
                logger.warning("Could not load preprocessing config from '%s': %s", prep_path, e)

        self.transforms = get_preprocessing_transforms(self.preprocessing_config)

        # 3. Check for model architecture config
        model_cfg_path = self.settings.resolved_model_config_path
        if model_cfg_path.exists():
            try:
                with open(model_cfg_path, encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    self.architecture = cfg_data.get("architecture", self.architecture)
            except Exception as e:
                logger.warning("Could not load model config from '%s': %s", model_cfg_path, e)

        # 4. Attempt to load trained model artifact if present
        model_path = self.settings.resolved_model_path
        self.artifact_path = model_path
        self.artifact_exists = model_path.exists() and model_path.is_file()

        if self.artifact_exists:
            try:
                logger.info("Attempting to load trained model from '%s'...", model_path)
                self._load_trained_artifact(model_path)
                self.model_source = "trained_model"
                self.is_loaded = True
                self.is_fallback = False
                logger.info(
                    "Successfully loaded trained model artifact (%s, %s, %d classes) from '%s'",
                    self.architecture,
                    self.artifact_type,
                    len(self.class_names),
                    model_path,
                )
                self.log_audit()
                return
            except Exception as e:
                logger.error(
                    "CRITICAL: Failed to load trained model artifact from '%s':\n%s",
                    model_path,
                    traceback.format_exc(),
                )
                # Fail explicitly rather than falling back silently to random weights
                self.model = None
                self.is_loaded = False
                self.artifact_type = "corrupt"

        # 5. If no trained model artifact exists or failed, check kNN fallback availability
        logger.info("No valid trained classifier artifact found at '%s'. Checking kNN fallback...", model_path)
        if self._check_knn_fallback_available():
            self.model_source = "retrieval_knn_fallback"
            self.is_loaded = True
            self.is_fallback = True
            logger.info("FruitClassifier configured with DINOv2 + Qdrant kNN fallback.")
        else:
            self.model_source = "unavailable"
            self.is_loaded = False
            self.is_fallback = True
            logger.warning("FruitClassifier unavailable: Neither trained artifact nor kNN retrieval service is operational.")

        self.log_audit()

    def _load_canonical_class_names(self) -> list[str]:
        """Load and validate target class list against canonical configs/classes.yaml."""
        # 1. Try class_names.json first if exists
        class_names_path = self.settings.resolved_class_names_path
        json_classes: list[str] | None = None
        if class_names_path.exists():
            try:
                with open(class_names_path, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        json_classes = data
                    elif isinstance(data, dict) and "classes" in data:
                        json_classes = data["classes"]
            except Exception as e:
                logger.warning("Could not load class names from '%s': %s", class_names_path, e)

        # 2. Canonical source of truth: configs/classes.yaml
        yaml_path = self.settings.resolved_class_mapping_path.parent / "classes.yaml"
        if not yaml_path.exists():
            yaml_path = Path(__file__).resolve().parents[3] / "configs" / "classes.yaml"

        canonical_classes: list[str] = []
        if yaml_path.exists():
            try:
                yaml_data = load_yaml_config(yaml_path)
                if "classes" in yaml_data and isinstance(yaml_data["classes"], list):
                    canonical_classes = [c.strip() for c in yaml_data["classes"]]
            except Exception as e:
                logger.warning("Could not load canonical classes from '%s': %s", yaml_path, e)

        if not canonical_classes:
            canonical_classes = [
                "apple", "avocado", "banana", "cherry", "grape", "guava", "kiwi",
                "lemon", "lychee", "mango", "orange", "papaya", "pear", "pineapple",
                "pomegranate", "strawberry", "tomato", "watermelon"
            ]

        # 3. Validate class metadata consistency if JSON classes were found
        if json_classes is not None:
            if len(json_classes) != len(canonical_classes):
                logger.warning(
                    "Class count mismatch: JSON (%d) vs Canonical (%d). Using canonical.",
                    len(json_classes),
                    len(canonical_classes),
                )
            elif json_classes != canonical_classes:
                logger.warning("Class order mismatch between JSON and canonical classes.yaml. Enforcing canonical order.")

        return canonical_classes

    def _load_trained_artifact(self, model_path: Path) -> None:
        """
        Flexibly load a PyTorch model artifact supporting multiple formats:
        1. TorchScript (.pt / .pth)
        2. Full nn.Module object
        3. Checkpoint dict containing 'state_dict' or 'model_state_dict'
        4. Raw state_dict
        """
        num_classes = len(self.class_names)

        # Strategy 1: Attempt TorchScript load
        try:
            model = torch.jit.load(str(model_path), map_location=self.device)
            self._validate_model(model, num_classes)
            self.model = model
            self.artifact_type = "torchscript"
            return
        except Exception:
            logger.debug("Artifact is not a TorchScript model. Trying PyTorch weight loaders...")

        # Strategy 2: Attempt standard PyTorch load
        loaded_obj = torch.load(str(model_path), map_location=self.device)

        # Strategy 2A: Full nn.Module
        if isinstance(loaded_obj, nn.Module):
            model = loaded_obj
            self._validate_model(model, num_classes)
            self.model = model
            self.artifact_type = "full_module"
            return

        # Extract state dict if inside a dictionary checkpoint
        state_dict: dict[str, Any] | None = None
        if isinstance(loaded_obj, dict):
            if "state_dict" in loaded_obj:
                state_dict = loaded_obj["state_dict"]
                self.artifact_type = "checkpoint_dict"
            elif "model_state_dict" in loaded_obj:
                state_dict = loaded_obj["model_state_dict"]
                self.artifact_type = "checkpoint_dict"
            else:
                # Could be a raw state_dict represented as a dict
                state_dict = loaded_obj
                self.artifact_type = "state_dict"

        if state_dict is not None and isinstance(state_dict, dict):
            model = build_model_architecture(self.architecture, num_classes)
            model.load_state_dict(state_dict)
            self._validate_model(model, num_classes)
            self.model = model
            return

        raise ModelLoadError(
            message=f"Unrecognized PyTorch model artifact format in '{model_path}'",
            detail=f"Loaded object type: {type(loaded_obj)}",
        )

    def _validate_model(self, model: Any, expected_classes: int) -> None:
        """Validate loaded model shape and execution via dummy inference."""
        model.to(self.device)
        model.eval()
        dummy_input = torch.zeros(1, 3, 224, 224, device=self.device)

        with torch.inference_mode():
            output = model(dummy_input)

        if not isinstance(output, torch.Tensor):
            raise ValueError(f"Model output must be a torch.Tensor, got {type(output)}")

        if output.dim() != 2 or output.shape[0] != 1 or output.shape[1] != expected_classes:
            raise ValueError(
                f"Model output dimension mismatch: Expected [1, {expected_classes}], "
                f"got {list(output.shape)}"
            )

    def _check_knn_fallback_available(self) -> bool:
        """Check if DINOv2 encoder and Qdrant repository are available for kNN fallback."""
        try:
            from app.ml.image_encoder import get_image_encoder
            from app.repositories.qdrant_repository import get_qdrant_repository

            encoder = get_image_encoder()
            qdrant = get_qdrant_repository()

            # Encoder model loading can be lazy, but Qdrant connectivity is required
            qdrant_ok, collection_ok = qdrant.get_health_status()
            return qdrant_ok and collection_ok
        except Exception as e:
            logger.warning("kNN fallback health check failed: %s", e)
            return False

    def get_audit_info(self) -> dict[str, Any]:
        """Return structured diagnostic audit metadata."""
        return {
            "architecture": self.architecture,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "artifact_exists": self.artifact_exists,
            "artifact_type": self.artifact_type,
            "classes_count": len(self.class_names),
            "classes": self.class_names,
            "preprocessing_source": (
                str(self.settings.resolved_preprocessing_config_path)
                if self.settings.resolved_preprocessing_config_path.exists()
                else "ImageNet defaults"
            ),
            "device": str(self.device),
            "model_source": self.model_source,
            "ready": self.is_loaded and self.model_source != "unavailable",
            "is_fallback": self.is_fallback,
        }

    def log_audit(self) -> None:
        """Log structured audit information to standard logger."""
        info = self.get_audit_info()
        logger.info(
            "Fruit Classifier Audit:\n"
            "  Architecture: %s\n"
            "  Artifact: %s\n"
            "  Artifact Exists: %s\n"
            "  Artifact Type: %s\n"
            "  Classes: %d\n"
            "  Preprocessing: %s\n"
            "  Device: %s\n"
            "  Model Source: %s\n"
            "  Ready: %s\n"
            "  Is Fallback: %s",
            info["architecture"],
            info["artifact_path"],
            info["artifact_exists"],
            info["artifact_type"],
            info["classes_count"],
            info["preprocessing_source"],
            info["device"],
            info["model_source"],
            info["ready"],
            info["is_fallback"],
        )

    def predict(self, image: Image.Image, top_k: int = 3) -> dict[str, Any]:
        """
        Run fruit classification inference.

        Delegates to:
        - Trained PyTorch model if loaded
        - DINOv2 + Qdrant kNN fallback if trained model is missing
        - Throws ModelNotLoadedError if neither engine is available.

        Returns structured dictionary containing predictions and engine metadata.
        """
        if not self.is_loaded or self.model_source == "unavailable":
            raise ModelNotLoadedError(
                message="Fruit classification model is not available.",
                detail="Neither trained model artifact nor kNN fallback service is ready.",
            )

        if self.model_source == "trained_model" and self.model is not None:
            return self._predict_trained_model(image, top_k)

        if self.model_source == "retrieval_knn_fallback":
            return self._predict_via_knn(image, top_k)

        raise ModelNotLoadedError(
            message="Classifier model is in an invalid state.",
            detail=f"model_source='{self.model_source}'",
        )

    def _predict_trained_model(self, image: Image.Image, top_k: int) -> dict[str, Any]:
        """Inference via trained PyTorch model."""
        try:
            rgb_image = image.convert("RGB")
            tensor = self.transforms(rgb_image).unsqueeze(0).to(self.device)

            with torch.inference_mode():
                logits = self.model(tensor)
                probabilities = F.softmax(logits, dim=1).squeeze(0)

            top_k = min(top_k, len(self.class_names))
            top_probs, top_indices = torch.topk(probabilities, k=top_k)

            predictions: list[tuple[str, float]] = []
            for prob, idx in zip(top_probs.tolist(), top_indices.tolist()):
                class_name = self.class_names[idx] if idx < len(self.class_names) else f"class_{idx}"
                predictions.append((class_name, round(float(prob), 4)))

            return {
                "predictions": predictions,
                "inference_method": self.architecture,
                "model_name": self.architecture,
                "model_source": "trained_artifact",
                "is_fallback": False,
            }
        except Exception as e:
            logger.error("Error during trained model inference: %s", e, exc_info=True)
            raise PredictionError(message="Failed to classify image.", detail=str(e)) from e

    def _predict_via_knn(self, image: Image.Image, top_k: int) -> dict[str, Any]:
        """
        Inference via DINOv2 + Qdrant 20-kNN similarity-weighted voting.

        1. Extract L2-normalized 768-dim embedding via DINOv2.
        2. Query Qdrant top-20 nearest neighbors.
        3. Filter neighbors below similarity_floor = 0.35.
        4. Compute similarity-weighted votes per canonical_class:
             weight(c) = sum(max(similarity - floor, 0))
        5. Normalize votes to get top-K probabilities.
        """
        try:
            from app.ml.image_encoder import get_image_encoder
            from app.repositories.qdrant_repository import get_qdrant_repository

            encoder = get_image_encoder()
            qdrant = get_qdrant_repository()

            # Ensure encoder is loaded
            if not encoder.is_loaded:
                encoder.load_model()

            # 1. Encode image
            embedding = encoder.encode_image(image)

            # 2. Query Qdrant top 20 nearest neighbors
            search_k = max(top_k * 4, 20)
            hits = qdrant.query_similar(embedding, top_k=search_k)

            if not hits:
                logger.warning("kNN classification returned 0 neighbors from Qdrant.")
                return {
                    "predictions": [(self.class_names[0], 0.0)],
                    "inference_method": "dinov2_qdrant_knn",
                    "model_name": "dinov2_base_qdrant_knn",
                    "model_source": "retrieval_knn_fallback",
                    "is_fallback": True,
                }

            # 3. Compute weighted votes per canonical class
            similarity_floor = 0.35
            class_weights: dict[str, float] = {}

            for hit in hits:
                cls = hit.canonical_class
                sim = hit.similarity
                if sim > similarity_floor:
                    weight = sim - similarity_floor
                    class_weights[cls] = class_weights.get(cls, 0.0) + weight

            total_weight = sum(class_weights.values())

            # If no neighbor met the similarity floor, fallback to unweighted top hits
            if total_weight <= 0:
                for hit in hits[:top_k]:
                    cls = hit.canonical_class
                    class_weights[cls] = class_weights.get(cls, 0.0) + max(hit.similarity, 0.01)
                total_weight = sum(class_weights.values())

            # 4. Normalize weights to probabilities
            sorted_classes = sorted(class_weights.items(), key=lambda x: x[1], reverse=True)

            predictions: list[tuple[str, float]] = []
            for cls, weight in sorted_classes[:top_k]:
                prob = weight / total_weight if total_weight > 0 else 0.0
                predictions.append((cls, round(float(prob), 4)))

            return {
                "predictions": predictions,
                "inference_method": "dinov2_qdrant_knn",
                "model_name": "dinov2_base_qdrant_knn",
                "model_source": "retrieval_knn_fallback",
                "is_fallback": True,
            }
        except Exception as e:
            logger.error("Error during kNN classification fallback: %s", e, exc_info=True)
            raise PredictionError(
                message="Failed to classify image via kNN fallback.", detail=str(e)
            ) from e


_classifier_instance: FruitClassifier | None = None


def get_fruit_classifier() -> FruitClassifier:
    """Return singleton FruitClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = FruitClassifier()
    return _classifier_instance
