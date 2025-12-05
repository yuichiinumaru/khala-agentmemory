from khala.application.utils import parse_json_safely, json_serializer
from datetime import datetime, date
import json

def test_parse_json_safely():
    # 1. Plain JSON
    assert parse_json_safely('{"a": 1}') == {"a": 1}

    # 2. Markdown
    assert parse_json_safely('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_safely('text before ```\n{"a": 1}\n``` text after') == {"a": 1}

    # 3. Dirty JSON
    assert parse_json_safely('Sure, here is json: {"a": 1} thanks') == {"a": 1}

    # 4. Empty
    assert parse_json_safely('') == {}

def test_json_serializer():
    dt = datetime(2025, 1, 1, 12, 0, 0)
    data = {"date": dt}
    serialized = json.dumps(data, default=json_serializer)
    assert "2025-01-01T12:00:00" in serialized
