from __future__ import annotations


# ---------------------------------------------------------------------------
# Word-level split (no overlap) — used when a single paragraph is too large
# ---------------------------------------------------------------------------

def _split_words(text, size):
    words = str(text or "").split()
    chunks = []
    start = 0
    total = len(words)
    while start < total:
        end = min(start + size, total)
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


# ---------------------------------------------------------------------------
# Fix 1: Overlap injection between adjacent chunks
# ---------------------------------------------------------------------------

def _add_overlap(chunks, overlap_words=150):
    """Prepend the tail of the previous chunk to the next one.

    Why this matters for legal documents
    -------------------------------------
    Legal clauses frequently span paragraph (and chunk) boundaries.
    Without overlap a clause like:

        Chunk 1 tail : "...the Lessee shall pay a security deposit of
                        Rs. 50,000 (Fifty Thousand Rupees)"
        Chunk 2 head : "which shall be refunded within 30 days of
                        vacating the premises, subject to deductions..."

    would be split. The model summarising Chunk 2 would have no idea
    what amount is being refunded or to whom.

    With 150-word overlap the critical context carries across and the
    model can produce accurate, complete clause summaries.

    overlap_words=150 is chosen deliberately:
    - Large enough to cover most multi-sentence legal clauses (~3-4 lines)
    - Small enough not to double-process entire sub-sections
    """
    if len(chunks) <= 1:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1].split()
        # Tail of the previous chunk — provides legal continuity context
        tail = " ".join(prev_words[-overlap_words:]) if len(prev_words) > overlap_words else chunks[i - 1]
        result.append(tail + "\n\n" + chunks[i])

    return result


# ---------------------------------------------------------------------------
# Main chunker
# ---------------------------------------------------------------------------

def chunk_document(text, min_words=1200, max_words=1500, overlap_words=150):
    """Split a large legal document into overlapping chunks.

    Parameters
    ----------
    min_words    : target minimum words per chunk
    max_words    : hard maximum words per chunk before forced split
    overlap_words: words from the tail of chunk[i] prepended to chunk[i+1]
                   (set to 0 to disable overlap)
    """
    paragraphs = [p.strip() for p in str(text or "").split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = []
    words = 0

    for para in paragraphs:
        count = len(para.split())

        # Paragraph itself exceeds max_words → force-split it
        if count > max_words:
            if current:
                chunks.append("\n\n".join(current).strip())
                current = []
                words = 0
            chunks.extend(_split_words(para, max_words))
            continue

        # Adding this paragraph would push over the limit → flush first
        if current and words + count > max_words:
            chunks.append("\n\n".join(current).strip())
            current = []
            words = 0

        current.append(para)
        words += count

        # Chunk is within the target window → seal it
        if min_words <= words <= max_words:
            chunks.append("\n\n".join(current).strip())
            current = []
            words = 0

    # Flush any remaining paragraphs
    if current:
        chunks.append("\n\n".join(current).strip())

    # ---------------------------------------------------------------------------
    # Fix 4: Safe last-chunk merge
    # ---------------------------------------------------------------------------
    # If the final chunk is too small (< min_words) it will not give the model
    # enough context for a useful summary.  Merge it with the previous chunk,
    # but ONLY if the merge stays within a reasonable size ceiling (2 × max_words)
    # so we never create a chunk the model cannot handle.
    if len(chunks) >= 2:
        last_count = len(chunks[-1].split())
        if last_count < min_words:
            merged = (chunks[-2] + "\n\n" + chunks[-1]).strip()
            merged_count = len(merged.split())
            if merged_count <= max_words * 2:
                chunks[-2] = merged
                chunks.pop()
            else:
                # Merge would be too large — leave the small tail chunk as-is
                # (better a slightly small chunk than an oversized one)
                pass

    # Remove any blank entries
    chunks = [c for c in chunks if c]

    # Ultimate fallback if nothing was produced
    if not chunks:
        return _split_words(text, max_words)

    # ---------------------------------------------------------------------------
    # Fix 1 (applied): inject overlap so legal clauses crossing boundaries
    # are visible to the model processing each chunk
    # ---------------------------------------------------------------------------
    if len(chunks) > 1 and overlap_words > 0:
        chunks = _add_overlap(chunks, overlap_words)

    return chunks


# ---------------------------------------------------------------------------
# Convenience class (backward-compatible)
# ---------------------------------------------------------------------------

class ImprovedChunker:
    def __init__(self, chunk_size=1500, overlap=150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_document(self, text):
        return chunk_document(text, max_words=self.chunk_size, overlap_words=self.overlap)
