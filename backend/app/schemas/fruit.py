"""
Pydantic schemas for Fruit Knowledge Base.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FruitNames(BaseModel):
    vi: str
    en: str


class FruitFamily(BaseModel):
    scientific: str
    vi: str


class FruitAppearance(BaseModel):
    color: list[str] = Field(default_factory=list)
    shape: str = ""
    size: str = ""
    peel: str = ""
    flesh: str = ""


class NutritionPer100g(BaseModel):
    calories_kcal: float | int = 0
    water_g: float | int = 0
    protein_g: float | int = 0
    carbohydrates_g: float | int = 0
    sugars_g: float | int = 0
    fiber_g: float | int = 0
    fat_g: float | int = 0


class FruitSource(BaseModel):
    title: str
    url: str


class FruitKnowledge(BaseModel):
    """Full detail schema for a canonical fruit species."""

    canonical_class: str
    names: FruitNames
    scientific_name: str
    family: FruitFamily
    description: str = ""
    origin: str = ""
    distribution: str = ""
    appearance: FruitAppearance = Field(default_factory=FruitAppearance)
    taste: str = ""
    texture: str = ""
    season: str = ""
    nutrition_per_100g: NutritionPer100g = Field(default_factory=NutritionPer100g)
    vitamins: list[str] = Field(default_factory=list)
    minerals: list[str] = Field(default_factory=list)
    key_compounds: list[str] = Field(default_factory=list)
    potential_health_benefits: list[str] = Field(default_factory=list)
    culinary_uses: list[str] = Field(default_factory=list)
    how_to_choose: list[str] = Field(default_factory=list)
    storage: list[str] = Field(default_factory=list)
    common_varieties: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    sources: list[FruitSource] = Field(default_factory=list)
