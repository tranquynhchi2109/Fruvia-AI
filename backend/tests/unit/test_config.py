"""
Unit tests for configuration loading and validation.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.core.config import Settings

pytestmark = pytest.mark.unit


class TestSettings:
    """Tests for the Settings configuration class."""

    def test_default_values(self) -> None:
        """Settings should have sensible defaults without any env vars."""
        with patch.dict(os.environ, {}, clear=True):
            s = Settings(_env_file=None)
        assert s.app_env == "development"
        assert s.app_port == 8000
        assert s.max_upload_mb == 10
        assert s.qdrant_collection == "fruvia_fruits360_original_dinov2_base_v1"
        assert s.log_level == "INFO"

    def test_max_upload_bytes(self) -> None:
        with patch.dict(os.environ, {"MAX_UPLOAD_MB": "5"}, clear=True):
            s = Settings()
        assert s.max_upload_bytes == 5 * 1024 * 1024

    def test_cors_origin_list_single(self) -> None:
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://localhost:3000"}, clear=True):
            s = Settings()
        assert s.cors_origin_list == ["http://localhost:3000"]

    def test_cors_origin_list_multiple(self) -> None:
        with patch.dict(
            os.environ,
            {"CORS_ORIGINS": "http://localhost:3000,http://localhost:8080"},
            clear=True,
        ):
            s = Settings()
        assert s.cors_origin_list == ["http://localhost:3000", "http://localhost:8080"]

    def test_is_production(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "production"}, clear=True):
            s = Settings()
        assert s.is_production is True

    def test_is_not_production(self) -> None:
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            s = Settings()
        assert s.is_production is False

    def test_invalid_log_level_rejected(self) -> None:
        with (
            patch.dict(os.environ, {"LOG_LEVEL": "VERBOSE"}, clear=True),
            pytest.raises(ValueError, match="log_level must be one of"),
        ):
            Settings()
