"""Small helpers around the Anthropic API."""
import json
import re

import anthropic

# Reads ANTHROPIC_API_KEY from the environment (your Codespaces secret)
client = anthropic.Anthropic()


def response_text(response) -> str:
    """Join all text blocks of a response (other block types are skipped)."""
    return "".join(block.text for block in response.content if block.type == "text")


def parse_json(text: str) -> dict:
    """Take the first {...} object out of a model answer and parse it."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    return json.loads(match.group(0))
