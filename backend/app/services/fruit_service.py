"""
Fruit Knowledge Base service.

Loads canonical fruit profiles from JSON and serves query requests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_ROOT
from app.core.logging import get_logger
from app.schemas.fruit import FruitKnowledge

logger = get_logger(__name__)

KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "data" / "fruit_knowledge.json"


class FruitKnowledgeService:
    """Service for retrieving structured fruit knowledge profiles."""

    def __init__(self, json_path: Path | None = None) -> None:
        self.json_path = json_path or KNOWLEDGE_BASE_PATH
        self._knowledge_data: dict[str, FruitKnowledge] = {}
        self._load_knowledge_base()

    def _load_knowledge_base(self) -> None:
        """Load and parse fruit_knowledge.json into schema objects."""
        if not self.json_path.exists():
            logger.error("Fruit Knowledge Base file not found at %s", self.json_path)
            return

        try:
            with open(self.json_path, encoding="utf-8") as f:
                raw_data: dict[str, Any] = json.load(f)

            parsed: dict[str, FruitKnowledge] = {}
            for key, val in raw_data.items():
                canonical_key = key.lower().strip()
                val["canonical_class"] = canonical_key
                parsed[canonical_key] = FruitKnowledge(**val)

            self._knowledge_data = parsed
            logger.info(
                "Successfully loaded %d fruit knowledge profiles from %s",
                len(self._knowledge_data),
                self.json_path,
            )
        except Exception as e:
            logger.error("Failed to load Fruit Knowledge Base: %s", e, exc_info=True)

    def get_fruit_knowledge(self, canonical_class: str) -> FruitKnowledge | None:
        """
        Get fruit knowledge profile by canonical_class slug.

        Parameters
        ----------
        canonical_class : str
            Canonical class slug (e.g. 'orange', 'apple')

        Returns
        -------
        FruitKnowledge | None
        """
        if not canonical_class:
            return None
        key = canonical_class.lower().strip().replace("-", "_")
        return self._knowledge_data.get(key)

    def list_canonical_classes(self) -> list[str]:
        """List all canonical class slugs present in the knowledge base."""
        return sorted(list(self._knowledge_data.keys()))


_knowledge_service_instance: FruitKnowledgeService | None = None


def get_fruit_knowledge_service() -> FruitKnowledgeService:
    """Return singleton FruitKnowledgeService instance."""
    global _knowledge_service_instance
    if _knowledge_service_instance is None:
        _knowledge_service_instance = FruitKnowledgeService()
    return _knowledge_service_instance
