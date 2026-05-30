# from __future__ import annotations

# import re

# _REPLACEMENTS = {"\x0c": " ", "\uf0b7": " ", "\u2022": " ", "\u00a0": " ", "\r": "\n"}
# _NOISE_LINE_PATTERNS = [
#     re.compile(r"^\s*page\s+\d+\s*(?:of\s+\d+)?\s*$", flags=re.IGNORECASE),
#     re.compile(r"^\s*(?:digitally|electronically)\s+signed\b.*$", flags=re.IGNORECASE),
#     re.compile(r"^\s*this\s+agreement\s+is\s+made\s+on\b.*$", flags=re.IGNORECASE),
# ]
# _IDENTITY_PATTERNS = [
#     re.compile(r"\bson\s+of\b[^,.;:\n]*", flags=re.IGNORECASE),
#     re.compile(r"\bdaughter\s+of\b[^,.;:\n]*", flags=re.IGNORECASE),
#     re.compile(r"\baged\s+about\b[^,.;:\n]*", flags=re.IGNORECASE),
#     re.compile(r"\b(?:residing|resident)\s+at\b[^.;:\n]*", flags=re.IGNORECASE),
#     re.compile(r"\bhereinafter\s+referred\s+to\s+as\b[^.;:\n]*", flags=re.IGNORECASE),
# ]
# _ADDRESS_LINE_HINT = re.compile(
#     r"\b(?:flat|floor|wing|sector|plot|road|street|lane|apartment|building|district|city|state|pin|pincode)\b",
#     flags=re.IGNORECASE,
# )

# def _fix_ocr_runs(text):
#     text = re.sub(r"(\b\d+)([A-Z]{3,}\b)", r"\1 \2", text)
#     text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
#     return re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)

# def _drop_noise_lines(text):
#     kept = []
#     for raw in str(text or "").split("\n"):
#         line = raw.strip()
#         if not line:
#             kept.append("")
#             continue
#         if any(pattern.match(line) for pattern in _NOISE_LINE_PATTERNS):
#             continue
#         if len(line) > 120 and _ADDRESS_LINE_HINT.search(line) and "," in line:
#             # Long address-heavy lines are typically non-operative metadata.
#             continue
#         kept.append(raw)
#     return "\n".join(kept)

# def _strip_identity_phrases(text):
#     cleaned = str(text or "")
#     for pattern in _IDENTITY_PATTERNS:
#         cleaned = pattern.sub("", cleaned)
#     return cleaned

# def _drop_repeated_lines(text):
#     output = []
#     previous_key = None
#     for raw in str(text or "").split("\n"):
#         line = raw.strip()
#         key = re.sub(r"\s+", " ", line).lower()
#         if key and key == previous_key:
#             continue
#         output.append(raw)
#         previous_key = key if key else None
#     return "\n".join(output)

# def _clean_numeric_noise(text):
#     cleaned = str(text or "")
#     cleaned = re.sub(r"\b(?:rs\.?|inr|usd|\$|€|£|₹)\s*(?:[,.-]+)\b", "", cleaned, flags=re.IGNORECASE)
#     cleaned = re.sub(r"\b\d[\d,]*[.,]\s*(?=[^\d]|$)", "", cleaned)
#     return cleaned

# def _is_heading_line(line):
#     line = re.sub(r"\s+", " ", line.strip(" :-\t"))
#     if not line:
#         return False
#     if len(line.split()) in range(13, 100):
#         return False
#     if line.endswith(".") or line.endswith(";") or line.endswith(","):
#         return False
#     if line == line.upper() and any(ch.isalpha() for ch in line):
#         return True
#     for prefix in ("article", "section", "clause"):
#         if line.lower().startswith(prefix + " "):
#             return True
#     if re.fullmatch(r"\d+(\.\d+)*[.)-]?\s+[A-Z][A-Z0-9\s/(),.-]{2,}", line):
#         return True
#     return False

# def remove_headings(text):
#     kept = []
#     for raw in str(text or "").split("\n"):
#         if raw.strip() and _is_heading_line(raw):
#             continue
#         kept.append(raw)
#     return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

# def clean_text(raw_text):
#     text = str(raw_text or "")
#     if not text.strip():
#         return ""
#     for source, target in _REPLACEMENTS.items():
#         text = text.replace(source, target)
#     text = _fix_ocr_runs(text)
#     text = _drop_noise_lines(text)
#     text = _strip_identity_phrases(text)
#     text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
#     text = re.sub(r"[ \t]+", " ", text)
#     text = re.sub(r" +\n", "\n", text)
#     text = re.sub(r"\n +", "\n", text)
#     text = remove_headings(text)
#     text = _drop_repeated_lines(text)
#     text = _clean_numeric_noise(text)
#     lines = []
#     for raw in text.split("\n"):
#         line = raw.strip()
#         if not line:
#             if lines and lines[-1] != "":
#                 lines.append("")
#             continue
#         if lines and lines[-1] and line[:1].islower():
#             lines[-1] = lines[-1] + " " + line
#         else:
#             lines.append(line)
#     text = "\n".join(lines)
#     text = re.sub(r"\n{3,}", "\n\n", text)
#     text = re.sub(r"\s+([,.;:!?])", r"\1", text)
#     text = re.sub(r"([,.;:!?])(\w)", r"\1 \2", text)
#     text = re.sub(r"([.?!]){2,}", r"\1", text)
#     return text.strip()

# def count_words(text):
#     return len(re.findall(r"\b\S+\b", str(text or "")))


from __future__ import annotations

import re

_REPLACEMENTS = {"\x0c": " ", "\uf0b7": " ", "\u2022": " ", "\u00a0": " ", "\r": "\n"}
_NOISE_LINE_PATTERNS = [
    re.compile(r"^\s*page\s+\d+\s*(?:of\s+\d+)?\s*$", flags=re.IGNORECASE),
    re.compile(r"^\s*(?:digitally|electronically)\s+signed\b.*$", flags=re.IGNORECASE),
    re.compile(r"^\s*this\s+agreement\s+is\s+made\s+on\b.*$", flags=re.IGNORECASE),
]
_IDENTITY_PATTERNS = [
    re.compile(r"\bson\s+of\b[^,.;:\n]*", flags=re.IGNORECASE),
    re.compile(r"\bdaughter\s+of\b[^,.;:\n]*", flags=re.IGNORECASE),
    re.compile(r"\baged\s+about\b[^,.;:\n]*", flags=re.IGNORECASE),
    re.compile(r"\b(?:residing|resident)\s+at\b[^.;:\n]*", flags=re.IGNORECASE),
    re.compile(r"\bhereinafter\s+referred\s+to\s+as\b[^.;:\n]*", flags=re.IGNORECASE),
]
_ADDRESS_LINE_HINT = re.compile(
    r"\b(?:flat|floor|wing|sector|plot|road|street|lane|apartment|building|district|city|state|pin|pincode)\b",
    flags=re.IGNORECASE,
)

def _fix_ocr_runs(text):
    text = re.sub(r"(\b\d+)([A-Z]{3,}\b)", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])(\d)", r"\1 \2", text)
    return re.sub(r"(\d)([A-Za-z])", r"\1 \2", text)

def _drop_noise_lines(text):
    kept = []
    for raw in str(text or "").split("\n"):
        line = raw.strip()
        if not line:
            kept.append("")
            continue
        if any(pattern.match(line) for pattern in _NOISE_LINE_PATTERNS):
            continue
        # Skip long address lines only in non-summarization mode (handled in clean_text)
        kept.append(raw)
    return "\n".join(kept)

def _drop_noise_lines_with_addresses(text):
    """Version that also removes long address lines - used for data extraction mode"""
    kept = []
    for raw in str(text or "").split("\n"):
        line = raw.strip()
        if not line:
            kept.append("")
            continue
        if any(pattern.match(line) for pattern in _NOISE_LINE_PATTERNS):
            continue
        if len(line) > 120 and _ADDRESS_LINE_HINT.search(line) and "," in line:
            # Long address-heavy lines are typically non-operative metadata.
            continue
        kept.append(raw)
    return "\n".join(kept)

def _strip_identity_phrases(text):
    cleaned = str(text or "")
    for pattern in _IDENTITY_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned

def _drop_repeated_lines(text):
    output = []
    previous_key = None
    for raw in str(text or "").split("\n"):
        line = raw.strip()
        key = re.sub(r"\s+", " ", line).lower()
        if key and key == previous_key:
            continue
        output.append(raw)
        previous_key = key if key else None
    return "\n".join(output)

def _clean_numeric_noise(text):
    cleaned = str(text or "")
    cleaned = re.sub(r"\b(?:rs\.?|inr|usd|\$|€|£|₹)\s*(?:[,.-]+)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d[\d,]*[.,]\s*(?=[^\d]|$)", "", cleaned)
    return cleaned

def _is_heading_line(line):
    line = re.sub(r"\s+", " ", line.strip(" :-\t"))
    if not line:
        return False
    if len(line.split()) in range(13, 100):
        return False
    if line.endswith(".") or line.endswith(";") or line.endswith(","):
        return False
    if line == line.upper() and any(ch.isalpha() for ch in line):
        return True
    for prefix in ("article", "section", "clause"):
        if line.lower().startswith(prefix + " "):
            return True
    if re.fullmatch(r"\d+(\.\d+)*[.)-]?\s+[A-Z][A-Z0-9\s/(),.-]{2,}", line):
        return True
    return False

def remove_headings(text):
    kept = []
    for raw in str(text or "").split("\n"):
        if raw.strip() and _is_heading_line(raw):
            continue
        kept.append(raw)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

def clean_text(raw_text, for_summarization=False):
    """
    Clean text from documents with optional modes.
    
    Args:
        raw_text: Raw text to clean
        for_summarization: If True, preserves headings, identities, and numeric context
                          If False, uses aggressive cleaning for data extraction/anonymization
    
    Returns:
        Cleaned text string
    """
    text = str(raw_text or "")
    if not text.strip():
        return ""
    
    # Basic character replacements - always safe
    for source, target in _REPLACEMENTS.items():
        text = text.replace(source, target)
    
    # Fix common extraction artifacts - always beneficial
    text = _fix_ocr_runs(text)
    
    # Drop noise lines (page numbers, signatures, etc.)
    if for_summarization:
        text = _drop_noise_lines(text)
    else:
        text = _drop_noise_lines_with_addresses(text)
    
    # Conditional cleaning based on mode
    if not for_summarization:
        # Only strip identities and numeric noise for data extraction
        text = _strip_identity_phrases(text)
        text = _clean_numeric_noise(text)
    
    # Merge hyphenated words across line breaks - always safe
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    
    # Whitespace normalization - always safe
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" +\n", "\n", text)
    text = re.sub(r"\n +", "\n", text)
    
    # Conditionally remove headings
    if not for_summarization:
        text = remove_headings(text)
    
    # Drop repeated lines - always beneficial
    text = _drop_repeated_lines(text)
    
    # Merge lines that continue mid-sentence
    lines = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        if lines and lines[-1] and line[:1].islower():
            lines[-1] = lines[-1] + " " + line
        else:
            lines.append(line)
    text = "\n".join(lines)
    
    # Final cleanup - always safe
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    text = re.sub(r"([,.;:!?])(\w)", r"\1 \2", text)
    text = re.sub(r"([.?!]){2,}", r"\1", text)
    
    return text.strip()

def count_words(text):
    return len(re.findall(r"\b\S+\b", str(text or "")))