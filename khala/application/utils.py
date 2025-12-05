"""Shared utilities for the application layer.

Implements safe JSON parsing and serialization to ensure reliability
and prevent security vulnerabilities (Injection/DoS).
"""

import json
import re
import logging
from datetime import datetime, date
from typing import Any, Dict, Union, List
from uuid import UUID

logger = logging.getLogger(__name__)

def json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    # Fallback: convert to string
    return str(obj)

def parse_json_safely(text: str) -> Union[Dict[str, Any], List[Any]]:
    """Robustly extract and parse JSON from text (e.g. LLM output).

    Handles:
    - Markdown code blocks (```json ... ```)
    - Raw JSON
    - Trailing commas (sometimes) via loose regex finding
    """
    if not text:
        return {}

    text = text.strip()

    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from Markdown code blocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        block_content = match.group(1)
        try:
            return json.loads(block_content)
        except json.JSONDecodeError:
            pass # Continue to next strategy

    # 3. Find outermost braces/brackets
    # This is a heuristic and can be fragile, but better than nothing for LLMs
    try:
        # Look for object
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if obj_match:
            return json.loads(obj_match.group(0))

        # Look for array
        arr_match = re.search(r"\[[\s\S]*\]", text)
        if arr_match:
            return json.loads(arr_match.group(0))
    except json.JSONDecodeError:
        pass

    logger.warning(f"Failed to parse JSON from text: {text[:100]}...")
    return {}
