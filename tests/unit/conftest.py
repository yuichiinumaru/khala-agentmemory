import sys
import os
from unittest.mock import MagicMock

# 1. Set Mock Environment Variables
os.environ["SURREAL_USER"] = "mock_user"
os.environ["SURREAL_PASS"] = "mock_pass"
os.environ["SURREAL_URL"] = "ws://mock:8000/rpc"
os.environ["GOOGLE_API_KEY"] = "mock_google_key"
os.environ["KHALA_API_KEY"] = "mock_khala_key"

# Mock dependencies globally before any test import
if "surrealdb" not in sys.modules:
    mock_surreal = MagicMock()
    class MockAsyncSurreal:
        pass
    mock_surreal.AsyncSurreal = MockAsyncSurreal
    mock_surreal.Surreal = MagicMock()

    mock_geometry = MagicMock()
    mock_geometry.GeometryPoint = MagicMock()

    sys.modules["surrealdb"] = mock_surreal
    sys.modules["surrealdb.data"] = MagicMock()
    sys.modules["surrealdb.data.types"] = MagicMock()
    sys.modules["surrealdb.data.types.geometry"] = mock_geometry

if "google.generativeai" not in sys.modules:
    sys.modules["google"] = MagicMock()
    sys.modules["google.generativeai"] = MagicMock()
    sys.modules["google.api_core"] = MagicMock()
    sys.modules["google.generativeai.types"] = MagicMock()

if "numpy" not in sys.modules:
    sys.modules["numpy"] = MagicMock()
