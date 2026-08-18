"""
Fruit Knowledge Base API routes.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.fruit import FruitKnowledge
from app.services.fruit_service import FruitKnowledgeService, get_fruit_knowledge_service

router = APIRouter(tags=["fruits"])


@router.get("/fruits", response_model=list[str])
async def list_fruits(
    service: Annotated[FruitKnowledgeService, Depends(get_fruit_knowledge_service)],
) -> list[str]:
    """Get list of all supported canonical fruit classes in the knowledge base."""
    return service.list_canonical_classes()


@router.get("/fruits/{canonical_class}", response_model=FruitKnowledge)
async def get_fruit_details(
    canonical_class: str,
    service: Annotated[FruitKnowledgeService, Depends(get_fruit_knowledge_service)],
) -> FruitKnowledge:
    """
    Get full biological and nutritional knowledge profile for a canonical fruit class.

    Parameters
    ----------
    canonical_class : str
        Canonical slug (e.g. 'orange', 'apple')
    """
    knowledge = service.get_fruit_knowledge(canonical_class)
    if knowledge is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fruit knowledge profile not found for '{canonical_class}'",
        )
    return knowledge
