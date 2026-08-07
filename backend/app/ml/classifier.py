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
    2. Fallback: DINOv2 + Qdrant 20-kNN hybrid scoring (Top-1 sim, Mean sim, Support ratio)
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

        if json_classes is not None and json_classes != canonical_classes:
            logger.warning("Class list mismatch between JSON and canonical classes.yaml. Enforcing canonical order.")

        return canonical_classes

    def _load_trained_artifact(self, model_path: Path) -> None:
        """Flexibly load a PyTorch model artifact supporting multiple formats."""
        num_classes = len(self.class_names)

        # Strategy 1: TorchScript
        try:
            model = torch.jit.load(str(model_path), map_location=self.device)
            self._validate_model(model, num_classes)
            self.model = model
            self.artifact_type = "torchscript"
            return
        except Exception:
            logger.debug("Artifact is not a TorchScript model. Trying PyTorch weight loaders...")

        # Strategy 2: PyTorch load
        loaded_obj = torch.load(str(model_path), map_location=self.device)

        if isinstance(loaded_obj, nn.Module):
            model = loaded_obj
            self._validate_model(model, num_classes)
            self.model = model
            self.artifact_type = "full_module"
            return

        state_dict: dict[str, Any] | None = None
        if isinstance(loaded_obj, dict):
            if "state_dict" in loaded_obj:
                state_dict = loaded_obj["state_dict"]
                self.artifact_type = "checkpoint_dict"
            elif "model_state_dict" in loaded_obj:
                state_dict = loaded_obj["model_state_dict"]
                self.artifact_type = "checkpoint_dict"
            else:
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
                "score_type": "softmax_probability",
                "inference_method": self.architecture,
                "model_name": self.architecture,
                "model_source": "trained_artifact",
                "is_fallback": False,
                "neighbor_agreement": None,
                "top_similarity": None,
            }
        except Exception as e:
            logger.error("Error during trained model inference: %s", e, exc_info=True)
            raise PredictionError(message="Failed to classify image.", detail=str(e)) from e

    def _predict_via_knn(self, image: Image.Image, top_k: int) -> dict[str, Any]:
        """
        Inference via DINOv2 + Qdrant 20-kNN Hybrid Decision Strategy.

        Scores each candidate class by combining:
        - 50% Top-1 Similarity: max(sim) for class
        - 30% Mean Similarity: avg(sim) for class
        - 20% Support Ratio: support_count / 20
        """
        try:
            from app.ml.image_encoder import get_image_encoder
            from app.repositories.qdrant_repository import get_qdrant_repository

            encoder = get_image_encoder()
            qdrant = get_qdrant_repository()

            if not encoder.is_loaded:
                encoder.load_model()

            embedding = encoder.encode_image(image)
            search_k = self.settings.knn_top_k
            hits = qdrant.query_similar(embedding, top_k=search_k)

            if not hits:
                logger.warning("kNN classification returned 0 neighbors from Qdrant.")
                return {
                    "predictions": [(self.class_names[0], 0.0)],
                    "score_type": "knn_vote",
                    "inference_method": "dinov2_qdrant_knn",
                    "model_name": "dinov2_base_qdrant_knn",
                    "model_source": "retrieval_knn_fallback",
                    "is_fallback": True,
                    "neighbor_agreement": "0/20",
                    "top_similarity": 0.0,
                    "winning_support": 0,
                    "winning_top_sim": 0.0,
                    "winning_margin": 0.0,
                }

            top_1_hit_sim = round(hits[0].similarity, 4)

            # Group hits by canonical class
            class_sims: dict[str, list[float]] = {}
            for hit in hits:
                cls = hit.canonical_class
                sim = hit.similarity
                if sim >= 0.25:  # Filter out negative or extreme low noise
                    class_sims.setdefault(cls, []).append(sim)

            if not class_sims:
                # If all hits are below 0.25
                first_cls = hits[0].canonical_class
                class_sims[first_cls] = [hits[0].similarity]

            # Compute Hybrid Score per class
            class_scores: dict[str, dict[str, float]] = {}
            total_k = float(len(hits))

            for cls, sims in class_sims.items():
                top1_sim = max(sims)
                mean_sim = sum(sims) / len(sims)
                support_ratio = len(sims) / total_k

                # Hybrid Formula
                hybrid_score = (0.50 * top1_sim) + (0.30 * mean_sim) + (0.20 * support_ratio)

                class_scores[cls] = {
                    "score": round(hybrid_score, 4),
                    "top1_sim": round(top1_sim, 4),
                    "mean_sim": round(mean_sim, 4),
                    "support": len(sims),
                }

            # Sort classes by hybrid_score descending
            sorted_classes = sorted(
                class_scores.items(), key=lambda x: x[1]["score"], reverse=True
            )

            winning_cls, winning_meta = sorted_classes[0]
            winning_support = winning_meta["support"]
            winning_top_sim = winning_meta["top1_sim"]

            runner_up_score = sorted_classes[1][1]["score"] if len(sorted_classes) > 1 else 0.0
            winning_margin = round(winning_meta["score"] - runner_up_score, 4)

            predictions: list[tuple[str, float]] = []
            for cls, meta in sorted_classes[:top_k]:
                predictions.append((cls, meta["score"]))

            agreement_str = f"{winning_support}/{len(hits)}"

            return {
                "predictions": predictions,
                "score_type": "knn_vote",
                "inference_method": "dinov2_qdrant_knn",
                "model_name": "dinov2_base_qdrant_knn",
                "model_source": "retrieval_knn_fallback",
                "is_fallback": True,
                "neighbor_agreement": agreement_str,
                "top_similarity": top_1_hit_sim,
                "winning_support": winning_support,
                "winning_top_sim": winning_top_sim,
                "winning_margin": winning_margin,
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
