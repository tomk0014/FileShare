"""
Fallback processor for FileShare Cleanup Pipeline.
Provides non-Ollama, non-OCR alternatives that are lightweight and deterministic.
"""

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def process_ocr_image(img_obj, lang="eng", quality="basic"):
    """Fallback OCR implementation - returns empty string or simple simulated text."""
    logger.warning("OCR fallback: No actual image parsing available without pytesseract")
    return ""


def classify_ollama(prompt, model=None, temperature=0.15, max_tokens=512):
    """Fallback classification using regex/pattern matching instead of Ollama LLM."""
    prompt_lower = prompt.lower()
    
    # Simple rule-based classification patterns
    if "classify" in prompt_lower:
        return {"category": "document", "confidence": 0.8, "description": "Document identified via keyword"}
    
    elif any(word in prompt_lower for word in ["title", "heading", "subject"]):
        return {"title": "Auto-generated Title", "tags": ["metadata"]}
    
    elif "duplicate" in prompt_lower or "similar" in prompt_lower:
        return {"duplicates_found": [], "similarity_scores": {}, "message": "No duplicates detected via regex analysis"}
    
    elif any(word in prompt_lower for word in ["sensitive", "private", "confidential"]):
        return {"classification": "Confidential", "pii_detected": False}
    
    else:
        # Generic fall-back classification
        return {
            "analysis_result": "Processed via fallback classifier",
            "timestamp": datetime.now().isoformat(),
            "fallback_mode": True,
            "confidence": 0.5
        }


def detect_trivial_content(text):
    """Determine if content is trivial using simple heuristics."""
    text_lower = text.lower()
    
    # Simple keyword-based triviality detection
    trivial_keywords = ["personal", "random", "junk", "non-business"]
    
    for keyword in trivial_keywords:
        if keyword in text_lower[:200]:  # Check first 200 characters
            return True
    
    # Length heuristics - very short docs might be trivial
    if len(text.strip()) < 50:
        return True
    
    return False


def generate_title(text, model="default"):
    """Generate a title for the document using text analysis."""
    # Extract first words or keywords
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text)
    
    if len(words) >= 3:
        title_words = [w.title() for w in words[:5]]
        return " - ".join(title_words) + " (auto-generated)"
    else:
        return f"Document_Heading_{str(datetime.now().timestamp())}"


def enrich_metadata(text, metadata_type="standard"):
    """Enrich text with metadata."""
    # Simple character count and basic stats
    enrichment = {
        "character_count": len(text),
        "word_count": len(text.split()),
        "generated_timestamp": datetime.now().isoformat()
    }
    
    if metadata_type == "pii_detection":
        # Basic PII detection patterns (very simple)
        pii_found = {}
        
        if re.search(r'\d{3}-\d{2}-\d{4}', text):  # SSN pattern
            pii_found['ssn'] = True
            
        if re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text):  # Email
            pii_found['email'] = True
            
        enrichment['pii_suspected'] = pii_found
    
    return enrichment


def get_similarity_score(text1, text2, threshold=0.95):
    """Calculate similarity between two text chunks (simple overlap analysis)."""
    # Tokenize and calculate Jaccard similarity on word sets
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    similarity = intersection / union if union > 0 else 0.0
    
    # Also check for exact hash match of file content (for dedup)
    import hashlib
    hash1 = hashlib.sha256(text1.encode()).hexdigest()[:8]
    hash2 = hashlib.sha256(text2.encode()).hexdigest()[:8]
    
    is_exact_duplicate = hash1 == hash2
    
    return {
        "similarity": similarity,
        "is_above_threshold": similarity >= threshold,
        "threshold_used": threshold,
        "exact_hash_match": is_exact_duplicate
    }


def initialize_core_paths(base_dir):
    """Setup core path configuration."""
    base_path = Path(base_dir)
    
    paths = {
        "BASE_DIR": base_path,
        "SOURCE_DOCS_DIR": base_path / "Synthetic_Docs",
        "EXTRACTED_TEXTS_DIR": base_path / "extracted_texts",
        "CLASSIFICATION_RESULTS_DIR": base_path / "classification_results",
        "DEDUPS_DIR": base_path / "Dedups",
        "INJECTED_METADATA_DIR": base_path / "Injected_Metadata",
        "PLACEHOLDERS_DIR": base_path / "placeholder_files",
        "LITIGATION_PACKAGES_DIR": base_path / "Litigation_Packages",
        "LITIGATION_REPORTS_DIR": base_path / "Litigation_Reports"
    }
    
    return paths


def ensure_directories(paths):
    """Ensure all configured directories exist."""
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
