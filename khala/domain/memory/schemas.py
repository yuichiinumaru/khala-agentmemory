"""Pydantic schemas for entity metadata validation.

Strategy 120: Custom Pydantic Entity Types.
Enforces strict typing on entity metadata based on entity type.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BaseEntitySchema(BaseModel):
    """Base schema for all entities."""
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    source_id: Optional[str] = None
    confidence_score: Optional[float] = None

class PersonSchema(BaseEntitySchema):
    """Schema for PERSON entities."""
    role: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None

class OrganizationSchema(BaseEntitySchema):
    """Schema for ORGANIZATION entities."""
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    founded_year: Optional[int] = None

class PlaceSchema(BaseEntitySchema):
    """Schema for PLACE entities."""
    coordinates: Optional[List[float]] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None  # e.g. "Restaurant", "Park"

class EventSchema(BaseEntitySchema):
    """Schema for EVENT entities."""
    date: Optional[str] = None
    location: Optional[str] = None
    participants: List[str] = Field(default_factory=list)
    status: Optional[str] = None

class ToolSchema(BaseEntitySchema):
    """Schema for TOOL entities."""
    version: Optional[str] = None
    language: Optional[str] = None
    repository: Optional[str] = None

class ConceptSchema(BaseEntitySchema):
    """Schema for CONCEPT entities."""
    domain: Optional[str] = None
    related_concepts: List[str] = Field(default_factory=list)
    complexity: Optional[str] = None

# Map entity types to schemas
# Using string keys matching EntityType enum values
ENTITY_SCHEMAS = {
    "person": PersonSchema,
    "organization": OrganizationSchema,
    "place": PlaceSchema,
    "event": EventSchema,
    "tool": ToolSchema,
    "concept": ConceptSchema,
}
