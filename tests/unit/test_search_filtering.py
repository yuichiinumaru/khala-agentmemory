"""Unit tests for SurrealDB client filtering functionality.

These tests verify that the _build_filter_query method correctly constructs
WHERE clauses for various filter types.
"""

import pytest
from unittest.mock import MagicMock
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestSurrealDBClientFiltering:
    """Test cases for SurrealDB filtering logic."""

    @pytest.fixture
    def client(self):
        """Create a test client instance."""
        return SurrealDBClient()

    def test_build_filter_query_empty(self, client):
        """Test with empty filters."""
        params = {}
        clause = client._build_filter_query({}, params)
        assert clause == ""
        assert params == {}

    def test_build_filter_query_simple_equality(self, client):
        """Test simple equality filters."""
        filters = {"category": "work", "is_public": True}
        params = {}

        clause = client._build_filter_query(filters, params)

        assert "category = $filter_category" in clause
        assert "is_public = $filter_is_public" in clause
        assert "AND" in clause
        assert params["filter_category"] == "work"
        assert params["filter_is_public"] is True

    def test_build_filter_query_list_inclusion(self, client):
        """Test list inclusion (IN operator)."""
        filters = {"tags": ["python", "ai"]}
        params = {}

        clause = client._build_filter_query(filters, params)

        assert "tags IN $filter_tags" in clause
        assert params["filter_tags"] == ["python", "ai"]

    def test_build_filter_query_complex_ops(self, client):
        """Test complex operators (gt, lt, contains)."""
        filters = {
            "age": {"op": "gt", "value": 18},
            "score": {"op": "lte", "value": 100},
            "name": {"op": "contains", "value": "John"}
        }
        params = {}

        clause = client._build_filter_query(filters, params)

        assert "age > $filter_age" in clause
        assert "score <= $filter_score" in clause
        assert "string::contains(name, $filter_name)" in clause
        assert params["filter_age"] == 18
        assert params["filter_score"] == 100
        assert params["filter_name"] == "John"

    def test_build_filter_query_nested_keys(self, client):
        """Test nested keys with dot notation."""
        filters = {"metadata.source": "web"}
        params = {}

        clause = client._build_filter_query(filters, params)

        assert "metadata.source = $filter_metadata_source" in clause
        assert params["filter_metadata_source"] == "web"

    def test_build_filter_query_sanitization(self, client):
        """Test that invalid keys are skipped."""
        filters = {"invalid;key": "value", "valid_key": "value"}
        params = {}

        clause = client._build_filter_query(filters, params)

        assert "valid_key" in clause
        assert "invalid;key" not in clause
