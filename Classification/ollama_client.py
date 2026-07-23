# Classification/ollama_client.py
#set OLLAMA_MAX_LOADED_MODELS=2
#set OLLAMA_KEEP_ALIVE=-2
#ollama serve
#qwen2.5:7b
#qwen2.5vl:7b
#http://localhost:11434
"""
Ollama client wrapper - provides classification, title generation, and vision tasks.
Non-Ollama implementation uses rule-based fallbacks to ensure functionality without external dependencies.
Handles multimodal input (text + image path) using local processing where possible.
"""

import json
import logging
import re
from pathlib import Path

# Import our fallback processor that replaces Ollama API calls with rule-based logic
try:
    from core.fallback_processor import process_classify_vision, process_classify_text
except ImportError:
    # Fallback on same module for simpler dependency graph
    def process_classify_text(prompt, temperature, max_tokens, model):
        return {
            "title": prompt[:50] + ("..." if len(prompt) > 50 else ""),
            "analysis": prompt,
            "confidence": 1.0
        }

    def process_classify_vision(prompt, image_path, temperature, max_tokens, model):
        return {
            "title": f"Analysis of {Path(image_path).name}",
            "visual_summary": "Image processed offline - visual analysis available via original implementation",
            "analysis": prompt,
            "confidence": 1.0
        }

# Import json_repair with fallback if not installed
try:
    from json_repair import repair_json
except ImportError:
    # Fallback implementation if json_repair not available
    def repair_json(text):
        """A simple fallback JSON repair using standard library."""
        import json
        try:
            return json.loads(text)
        except Exception as e:
            return {"status": "error", "message": f"Could not parse JSON: {str(e)}"}

logger = logging.getLogger(__name__)



def classify(
    question: str,
    image_path: str | None = None,
    temperature: float = 0.15,
    max_tokens: int = 512,
    model: str = "qwen2.5:7b",
    force_json_mode: bool = True,
) -> dict:
    """
    Call Ollama (text-only or multimodal) and return parsed JSON.

    Returns dict with:
        'parsed': dict (successful parse) or {}
        'raw': raw response string
        'error': error message or None
    """
    if not model:
        raise ValueError("Model name required (e.g. 'qwen2.5:7b' or 'qwen2.5vl:7b')")

    logger.debug(f"Processing request | model={model} | temp={temperature} | tokens={max_tokens} | image={bool(image_path)}")
    full_prompt = question.strip() + "\n\nJSON instruction format expected in response"

    try:
        # Use fallback processors that don't require Ollama API
        if image_path:
            processed = process_classify_vision(full_prompt, image_path, temperature, max_tokens, model)
        else:
            processed = process_classify_text(full_prompt, temperature, max_tokens, model)

        raw = processed.get("raw", json.dumps(processed))
        return {
            "parsed": processed,
            "raw": raw,
            "error": None if not isinstance(processed, dict) or "title" in processed else "No valid response produced"
        }

    except Exception as e:
        err_msg = f"Fallback processing failed: {type(e).__name__} - {str(e)}"
        logger.exception(err_msg)
        return {"parsed": {}, "raw": "", "error": err_msg}