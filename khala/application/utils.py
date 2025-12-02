import json
import logging
import ast
from typing import Any

logger = logging.getLogger(__name__)

def parse_json_safely(content: str) -> Any:
    """
    Helper to safely parse JSON from LLM output.
    Handles Markdown code blocks and single-quoted JSON-like strings.
    """
    content = content.strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Fallback for Python dict/list string representation
        if (content.startswith("{") and content.endswith("}")) or \
           (content.startswith("[") and content.endswith("]")):
             try:
                return ast.literal_eval(content)
             except Exception:
                pass
        logger.warning(f"Failed to parse JSON content: {content[:100]}...")
        return None
