"""Metadata validation utility for KHALA.

This module provides tools for validating arbitrary metadata against JSON schemas,
enabling Strategy 64: Schema-Flexible Metadata.
"""

from typing import Dict, Any, Optional
import logging
import json
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)


class MetadataValidator:
    """Validator for schema-flexible metadata."""

    @staticmethod
    def validate_metadata(metadata: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate metadata against a JSON schema.

        Args:
            metadata: The metadata dictionary to validate.
            schema: The JSON schema to validate against.

        Returns:
            True if valid, False otherwise.

        Raises:
            ValidationError: If validation fails and raise_error is True (implicit in jsonschema).
        """
        try:
            validate(instance=metadata, schema=schema)
            return True
        except ValidationError as e:
            logger.warning(f"Metadata validation failed: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during metadata validation: {e}")
            return False

    @staticmethod
    def validate_and_raise(metadata: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """Validate metadata and raise ValidationError on failure.

        Args:
            metadata: The metadata dictionary to validate.
            schema: The JSON schema to validate against.

        Raises:
            ValidationError: If validation fails.
        """
        validate(instance=metadata, schema=schema)
