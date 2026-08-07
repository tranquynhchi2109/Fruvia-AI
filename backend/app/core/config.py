"""
Fruvia AI application settings.

All configuration is loaded from environment variables via Pydantic Settings.
No secret is ever hardcoded — see .env.example for the full list.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Unified Project Root resolution (works for both local Windows and Docker)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path) -> Path:
    """
    Resolve path relative to PROJECT_ROOT if it is a relative path or if the
    absolute path does not exist on the current system (e.g. Docker container paths
    like /app/models/... when running on Windows).
    """
    p = Path(path)
    if p.is_absolute():
        if p.exists():
            return p
        # If absolute path doesn't exist (e.g. /app/models/...), resolve relative to PROJECT_ROOT
        relative_parts = p.parts[1:] if p.parts[0] in ("/", "\\") else p.parts
        # Strip leading container directory if present
        if relative_parts and relative_parts[0] == "app":
            relative_parts = relative_parts[1:]
        candidate = PROJECT_ROOT.joinpath(*relative_parts)
        return candidate
    return (PROJECT_ROOT / p).resolve()


class Settings(BaseSettings):
    """Central configuration read from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = Field(default="development", description="development | staging | production")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_version: str = Field(default="0.1.0")

    # --- DINOv2 Embedding Model ---
    dinov2_model_name: str = Field(
        default="facebook/dinov2-base", description="Hugging Face model repository ID"
    )
    dinov2_revision: str = Field(
        default="main", description="Pinned commit hash or revision tag for DINOv2 model"
    )
    hf_home: Path | None = Field(
        default=None, description="Optional custom directory for Hugging Face cache"
    )

    # --- Classification Model ---
    model_path: Path = Field(default=Path("models/classifier/model.pth"))
    class_names_path: Path = Field(default=Path("models/classifier/class_names.json"))
    model_config_path: Path = Field(default=Path("models/classifier/model_config.json"))
    preprocessing_config_path: Path = Field(default=Path("models/classifier/preprocessing.json"))

    # --- Classification Behavior ---
    classification_threshold: float = Field(
        default=0.65, ge=0.0, le=1.0, description="Minimum confidence to accept a prediction (Neural Net Softmax)"
    )

    # --- kNN Fallback Settings ---
    knn_min_top_similarity: float = Field(
        default=0.45, ge=0.0, le=1.0, description="Minimum similarity required for top neighbor hit"
    )
    knn_min_margin: float = Field(
        default=0.08, ge=0.0, le=1.0, description="Minimum margin between top-1 and top-2 class scores"
    )
    knn_min_support: int = Field(
        default=3, ge=1, le=20, description="Minimum neighbor support count out of 20"
    )
    knn_top_k: int = Field(
        default=20, ge=1, le=50, description="Number of nearest neighbors to query for kNN voting"
    )

    # --- Qdrant ---
    qdrant_url: str | None = Field(default=None, description="Qdrant Cloud endpoint URL")
    qdrant_api_key: str | None = Field(default=None, description="Qdrant Cloud API key")
    qdrant_collection: str = Field(default="fruvia_fruits360_original_dinov2_base_v1")
    qdrant_timeout: int = Field(default=10, description="Qdrant request timeout in seconds")

    # --- Upload ---
    max_upload_mb: int = Field(default=10, ge=1, le=50)
    max_image_pixels: int = Field(
        default=25_000_000, description="Maximum total pixel count to prevent decompression bombs"
    )
    max_image_width: int = Field(default=5000, description="Maximum image width in pixels")
    max_image_height: int = Field(default=5000, description="Maximum image height in pixels")
    class_mapping_path: Path = Field(
        default=Path("configs/class_mapping.yaml"),
        description="Path to original->canonical class mapping YAML",
    )

    # --- CORS ---
    cors_origins: str = Field(default="http://localhost:3000")

    # --- Logging ---
    log_level: str = Field(default="INFO")

    # --- Derived properties ---

    @property
    def resolved_model_path(self) -> Path:
        return resolve_path(self.model_path)

    @property
    def resolved_class_names_path(self) -> Path:
        return resolve_path(self.class_names_path)

    @property
    def resolved_model_config_path(self) -> Path:
        return resolve_path(self.model_config_path)

    @property
    def resolved_preprocessing_config_path(self) -> Path:
        return resolve_path(self.preprocessing_config_path)

    @property
    def resolved_class_mapping_path(self) -> Path:
        return resolve_path(self.class_mapping_path)

    @property
    def max_upload_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Call this instead of constructing Settings() directly so the
    environment is read only once.
    """
    return Settings()


def load_class_names(path: Path) -> list[str]:
    """Load the ordered list of class names from a JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "classes" in data:
        return data["classes"]
    raise ValueError(f"Unexpected class_names format in {path}")
