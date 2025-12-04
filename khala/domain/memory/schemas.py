"""Pydantic schemas for memory domain entity validation.

Strategy 120: Custom Pydantic Entity Types.
Enforces strict typing for entity metadata and API contracts.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl, EmailStr, validator
from datetime import datetime

class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    PERSON = "person"
    TOOL = "tool"
    CONCEPT = "concept"
    PLACE = "place"
    EVENT = "event"
    ORGANIZATION = "organization"
    DATE = "date"
    NUMBER = "number"

class BaseEntitySchema(BaseModel):
    """Base schema for all entity metadata."""
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

    class Config:
        extra = "allow"  # Allow extra fields for flexibility

class PersonSchema(BaseEntitySchema):
    """Schema for Person entity metadata."""
    role: Optional[str] = None
    email: Optional[EmailStr] = None
    affiliation: Optional[str] = None

class OrganizationSchema(BaseEntitySchema):
    """Schema for Organization entity metadata."""
    industry: Optional[str] = None
    headquarters: Optional[str] = None
    website: Optional[HttpUrl] = None

class ToolSchema(BaseEntitySchema):
    """Schema for Tool entity metadata."""
    version: Optional[str] = None
    language: Optional[str] = None
    documentation_url: Optional[HttpUrl] = None

class PlaceSchema(BaseEntitySchema):
    """Schema for Place entity metadata."""
    coordinates: Optional[List[float]] = Field(None, min_items=2, max_items=2)
    country: Optional[str] = None
    city: Optional[str] = None

class EventSchema(BaseEntitySchema):
    """Schema for Event entity metadata."""
    date: Optional[datetime] = None
    location: Optional[str] = None
    participants: List[str] = Field(default_factory=list)

class EntityMetadataValidator:
    """Validator for entity metadata based on type."""

    @staticmethod
    def validate(entity_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata against the appropriate schema."""
        schema_map = {
            EntityType.PERSON.value: PersonSchema,
            EntityType.ORGANIZATION.value: OrganizationSchema,
            EntityType.TOOL.value: ToolSchema,
            EntityType.PLACE.value: PlaceSchema,
            EntityType.EVENT.value: EventSchema,
        }

        schema_cls = schema_map.get(entity_type)
        if schema_cls:
            # Validate and return dict
            return schema_cls(**metadata).model_dump(exclude_none=True)
        return metadata
