"""
Unit tests for Fruit Knowledge Base service and API endpoints.
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.fruit_service import FruitKnowledgeService, get_fruit_knowledge_service

pytestmark = pytest.mark.unit


@pytest.fixture
def knowledge_service() -> FruitKnowledgeService:
    return get_fruit_knowledge_service()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestFruitKnowledgeService:
    """Tests for FruitKnowledgeService."""

    def test_list_canonical_classes(self, knowledge_service: FruitKnowledgeService) -> None:
        classes = knowledge_service.list_canonical_classes()
        assert len(classes) == 18
        assert "orange" in classes
        assert "apple" in classes

    def test_get_valid_fruit_knowledge(self, knowledge_service: FruitKnowledgeService) -> None:
        orange = knowledge_service.get_fruit_knowledge("orange")
        assert orange is not None
        assert orange.canonical_class == "orange"
        assert orange.scientific_name == "Citrus sinensis"
        assert orange.family.scientific == "Rutaceae"
        assert orange.nutrition_per_100g.calories_kcal == 47

    def test_get_fruit_knowledge_case_insensitive(self, knowledge_service: FruitKnowledgeService) -> None:
        orange = knowledge_service.get_fruit_knowledge("ORANGE")
        assert orange is not None
        assert orange.canonical_class == "orange"

    def test_unknown_fruit_returns_none(self, knowledge_service: FruitKnowledgeService) -> None:
        result = knowledge_service.get_fruit_knowledge("unknown_alien_fruit")
        assert result is None


class TestFruitKnowledgeAPI:
    """Tests for GET /api/fruits endpoints."""

    def test_list_fruits_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/fruits")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 18
        assert "orange" in data

    def test_get_fruit_details_success(self, client: TestClient) -> None:
        resp = client.get("/api/fruits/orange")
        assert resp.status_code == 200
        data = resp.json()
        assert data["canonical_class"] == "orange"
        assert data["scientific_name"] == "Citrus sinensis"
        assert "names" in data
        assert data["names"]["vi"] == "Cam"

    def test_get_fruit_details_not_found(self, client: TestClient) -> None:
        resp = client.get("/api/fruits/non_existent_fruit")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
