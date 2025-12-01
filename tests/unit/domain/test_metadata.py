"""Unit tests for MetadataValidator."""

import pytest
from jsonschema import ValidationError
from khala.domain.memory.metadata import MetadataValidator


class TestMetadataValidator:
    """Test suite for MetadataValidator."""

    def test_validate_metadata_valid(self):
        """Test validation with valid metadata."""
        schema = {
            "type": "object",
            "properties": {
                "author": {"type": "string"},
                "version": {"type": "integer"},
            },
            "required": ["author", "version"],
        }
        metadata = {"author": "Jules", "version": 1}

        assert MetadataValidator.validate_metadata(metadata, schema) is True

    def test_validate_metadata_invalid(self):
        """Test validation with invalid metadata."""
        schema = {
            "type": "object",
            "properties": {
                "author": {"type": "string"},
                "version": {"type": "integer"},
            },
            "required": ["author", "version"],
        }
        metadata = {"author": "Jules", "version": "1.0"}  # version should be integer

        assert MetadataValidator.validate_metadata(metadata, schema) is False

    def test_validate_metadata_missing_field(self):
        """Test validation with missing required field."""
        schema = {
            "type": "object",
            "required": ["required_field"],
        }
        metadata = {"other_field": "value"}

        assert MetadataValidator.validate_metadata(metadata, schema) is False

    def test_validate_and_raise_valid(self):
        """Test validate_and_raise with valid metadata."""
        schema = {"type": "string"}
        metadata = "valid string"

        # Should not raise exception
        MetadataValidator.validate_and_raise(metadata, schema)

    def test_validate_and_raise_invalid(self):
        """Test validate_and_raise with invalid metadata."""
        schema = {"type": "string"}
        metadata = 123

        with pytest.raises(ValidationError):
            MetadataValidator.validate_and_raise(metadata, schema)
