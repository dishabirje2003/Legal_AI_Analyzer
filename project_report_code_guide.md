# Code Artifacts & Modules Guide for Project Report

This guide outlines the core architectural modules, flowcharts, and key code snippets of the **Legal AI Analyzer** application. You can include these sections directly in your project report.

---

## 1. Intelligent Legal Summarization Engine
**File Location:** `backend/app/services/ai/legal_summarization.py`

### Description
The summarization engine transforms raw legal documents into high-quality extractive and abstractive summaries. It features:
*   **Dynamic Structure Resolution**: Tailors summaries to specific document categories (Contracts, Property Deeds, Court Judgments, Insurance Policies, Financial Agreements).
*   **Advanced Sequential & Sectional Chunking**: Groups long documents by logical section boundaries (`extract_sections`) to keep relative clauses together, falling back to sequential windowing if section markings are not present.
*   **Heuristic Sentence Scoring**: Extracted sentences are ranked mathematically based on legal importance keywords (`shall`, `must`, `agrees`, `liability`, `indemnify`, monetary symbols, and section references).

### Key Code Snippets

#### A. Heuristic Sentence Ranker (Extractive Summary)
```python
def _sentences(text):
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned: return []
    normalized = re.sub(r"([.!?])\s+", r"\1\n", cleaned)
    return [piece.strip() for piece in normalized.splitlines() if piece.strip()]

def _sentence_score(sentence):
    lowered = sentence.lower()
    score = 0
    high_priority = ("shall", "must", "agrees", "obligation", "liable", "indemnify", "terminate", "default", "penalty", "payment", "rent")
    for keyword in high_priority:
        if keyword in lowered: score += 3
    if any(ch.isdigit() for ch in sentence): score += 2
    if re.search(r"\b(?:Section|Clause|Article)\s+\d+", sentence, re.IGNORECASE): score += 3
    if re.search(r"(?:Rs\.?|INR|₹|USD|\$)", sentence, re.IGNORECASE): score += 3
    return score

def _select_extractive_sentences(text, limit=8):
    sentences = list(dict.fromkeys(_sentences(text)))
    if not sentences: return []
    ranked = sorted(enumerate(sentences), key=lambda item: (-_sentence_score(item[1]), item[0]))
    chosen = sorted(index for index, _ in ranked[:limit])
    return [sentences[index] for index in chosen]
```

#### B. Gemini API Client with Exponential Backoff
```python
class GeminiClient:
    async def generate(self, prompt, model_name=None, timeout_seconds=None):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        timeout = timeout_seconds or settings.gemini_timeout_seconds
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0, "topP": 0.1, "topK": 1},
        }
        retries = min(3, max(1, int(settings.gemini_max_retries or 3)))
        base_backoff = float(settings.gemini_rate_limit_backoff_seconds or 15.0)
        models = self._candidate_models(model_name or settings.gemini_model_name)
        last_error = None

        for model in models:
            for attempt in range(1, retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            API_URL.format(model=model),
                            params={"key": settings.gemini_api_key},
                            json=body,
                        )
                    if response.status_code == 404:
                        break
                    if response.status_code == 429:
                        if attempt < retries:
                            sleep_for = (base_backoff * attempt) + random.uniform(1.0, 3.0)
                            await asyncio.sleep(sleep_for)
                            continue
                        else:
                            last_error = RuntimeError(f"429 rate limit on {model}")
                            break
                    response.raise_for_status()
                    payload = response.json()
                    for candidate in payload.get("candidates") or []:
                        content = candidate.get("content") or {}
                        for part in content.get("parts") or []:
                            text = (part.get("text") or "").strip()
                            if text:
                                return text
                except Exception as exc:
                    last_error = exc
                    if attempt < retries:
                        await asyncio.sleep(base_backoff + random.uniform(1.0, 3.0))
                        continue
                    break
        raise RuntimeError(f"Gemini generation failed: {last_error}")
```

---

## 2. Quantitative Risk Assessment Engine
**File Location:** `backend/app/services/ai/risk_detection_service.py`

### Description
The Risk Assessment Engine extracts legal liabilities, vulnerabilities, and unfavorable clauses directly from the document's content.
*   **Document-Specific Prompting**: Prevents hallucinated warnings by strictly enforcing grounded, citation-based risk analysis.
*   **Formulaic Severity Scoring**: Automatically parses and grades the document's risk index, assigning penalty values depending on the severity of the detected threat (High: -18, Medium: -10, Low: -4).

### Key Code Snippets

#### A. Structured Risk Generation Prompt Template
```python
def _generate_risks_with_llm(text: str, document_type: str, document_id: str = None) -> List[Dict[str, Any]]:
    prompt = f"""You are a senior legal risk analyst AI.
Your task is to extract ONLY REAL, DOCUMENT-SPECIFIC legal risks from the provided legal document.

STRICT INSTRUCTIONS:
1. DO NOT generate generic or template risks.
2. Every risk MUST:
   - Be directly grounded in the document text
   - Reference a specific clause, section, or factual situation
   - Include a short explanation of WHY it is a risk
3. If the document does NOT contain meaningful risks:
   - Return an empty list []
   - DO NOT hallucinate or infer risks
4. Be precise and conservative: Prefer missing a risk over inventing one
5. Output MUST be valid JSON only (no markdown, no explanation)

OUTPUT FORMAT:
[
  {{
    "title": "Short risk title",
    "description": "Clear explanation tied to document content",
    "severity": "low | medium | high",
    "clause_reference": "Clause number or section if available"
  }}
]

DOCUMENT:
{text}
"""
```

#### B. Quantitative Score Calculator
```python
def detect_risks(
    clauses: List[Dict[str, Any]],
    entities: Dict[str, Any],
    text: str,
    structured_summary: Dict[str, Any] | None = None,
    document_type: str | None = None,
    document_id: str = None,
) -> Dict[str, Any]:
    try:
        llm_risks = _generate_risks_with_llm(text, document_type or "general", document_id)
        
        MAX_BY_SEVERITY = {"high": 5, "medium": 5, "low": 3}
        high_risks = [r for r in llm_risks if r["severity"] == "high"][: MAX_BY_SEVERITY["high"]]
        medium_risks = [r for r in llm_risks if r["severity"] == "medium"][: MAX_BY_SEVERITY["medium"]]
        low_risks = [r for r in llm_risks if r["severity"] == "low"][: MAX_BY_SEVERITY["low"]]

        kept_count = len(high_risks) + len(medium_risks) + len(low_risks)
        
        # Risk Score out of 100
        risk_score = max(0, 100 - (len(high_risks) * 18 + len(medium_risks) * 10 + len(low_risks) * 4))
        
        if high_risks or risk_score < 45:
            risk_level = "High"
        elif medium_risks or risk_score < 75:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "summary": {
                "risk_score": risk_score,
                "risk_level": risk_level,
                "contract_type": document_type or "general",
                "detected_patterns": len(llm_risks),
                "published_risks": kept_count,
            },
            "high_risks": high_risks,
            "medium_risks": medium_risks,
            "low_risks": low_risks,
            "status": "success"
        }
```

---

## 3. Pre-Retrieval Intent-Routing Legal Q&A (RAG)
**File Location:** `backend/app/services/ai/rag_service.py`

### Description
The Q&A RAG Service functions as a smart legal assistant. Rather than running standard vector database lookups for every user query, it routes queries via an **Intent Classifier**:
1.  **Greeting, Help, & Off-Topic Filtering**: Instantly answers general prompts without using LLM/Vector resources.
2.  **Entity Listing & Entity Lookup**: Direct queries like *"Who is the landlord?"* or *"What is BBMP?"* bypass heavy semantic retrieval by using high-performance regex maps and cross-referencing structured Named Entity Recognition (NER) dictionaries.
3.  **Hybrid Retrieval (Semantic + Keyword)**: Connects to Pinecone for vector retrieval, falling back dynamically to a database-driven TF-IDF keyword match if Pinecone is offline or unconfigured.
4.  **Math-Based Retrieval Confidence Scorer**: Scores output trust using similarity weights, source density, and critical clause tags.

### Key Code Snippets

#### A. Pre-Retrieval Intent Router
```python
def classify_intent(query: str) -> str:
    q = query.strip()
    if _GREETING_PATTERNS.match(q):
        return 'greeting'
    if _HELP_PATTERNS.search(q):
        return 'help'
    if _OFF_TOPIC_PATTERNS.search(q):
        return 'off_topic'
    if _ENTITY_LOOKUP_PATTERNS.match(q):
        return 'entity_lookup'
    if _ENTITY_QUERY_PATTERNS.search(q):
        return 'entity_query'
    
    q_lower = q.lower()
    if any(kw in q_lower for kw in _LEGAL_ANALYSIS_KEYWORDS):
        return 'legal_analysis'
        
    return 'document_qa'
```

#### B. NER-Driven Entity Resolution Algorithm
```python
def _resolve_entity(entities: Dict[str, Any], search_term: str) -> Dict[str, Any] | None:
    enriched = entities.get("enriched", {})
    parties_dict = entities.get("parties_dict", {})
    term_lower = search_term.lower().strip()
    resolved_role = _ROLE_ALIASES.get(term_lower, term_lower)

    # 1. Role match via parties_dict ("lessor" -> "Mr. Rajesh Kumar")
    for role, name in parties_dict.items():
        if role.lower() == resolved_role or role.lower() == term_lower:
            return {
                "text": name,
                "role": role.title(),
                "category": "parties",
                "match_type": "role",
            }

    # 2. Category Search across Enriched Keys
    for cat_key, cat_label in category_labels.items():
        for item in enriched.get(cat_key, []):
            if not isinstance(item, dict): continue
            item_text = item.get("text", "")
            item_lower = item_text.lower()
            if item_lower == term_lower:
                return {"text": item_text, "category": cat_key, "match_type": "exact"}
            if term_lower in item_lower or item_lower in term_lower:
                return {"text": item_text, "category": cat_key, "match_type": "partial"}

    return None
```

#### C. Confidence Scorer
```python
def _calculate_confidence(sources: List[Dict], total_score: float) -> float:
    if not sources:
        return 0.0
    avg_score = total_score / len(sources)
    # Density coverage bonus
    coverage_bonus = min(0.15, len(sources) * 0.04)
    # Importance bonus
    critical_bonus = 0.05 if any(s.get("importance_label") == "Critical" for s in sources) else 0.0

    confidence = avg_score + coverage_bonus + critical_bonus
    return round(min(0.98, max(0.1, confidence)), 2)
```

---

## 4. Clause Intelligence & Attribution Service
**File Location:** `backend/app/services/ai/clause_detection_service.py`

### Description
Extracts individual legal provisions from documents, identifies the responsible party, calculates a weight-based importance score, and clusters similar clauses into structured groups.

### Key Code Snippet: Responsible Party Detection
This script parses grammatical structures and matches custom legal actor profiles (Lessor, Lessee, Lender, Borrower, Insurer, Insured) instead of classifying non-party organizations:
```python
def _detect_responsible_party(text: str, entities: Dict[str, Any]) -> str:
    text_lower = text.lower()
    parties_dict = entities.get("parties_dict", {})
    
    obligation_patterns = [
        (r'\b(lessor|landlord|owner)\b.*\b(shall|must|agrees|undertakes|is\s*required)\b', "Lessor"),
        (r'\b(lessee|tenant|renter)\b.*\b(shall|must|agrees|undertakes|is\s*required)\b', "Lessee"),
        (r'\b(buyer|purchaser)\b.*\b(shall|must|agrees|undertakes)\b', "Buyer"),
        (r'\b(seller|vendor)\b.*\b(shall|must|agrees|undertakes)\b', "Seller"),
        (r'\b(lender|bank)\b.*\b(shall|must|agrees)\b', "Lender"),
        (r'\b(borrower|debtor)\b.*\b(shall|must|agrees)\b', "Borrower"),
    ]
    
    matched_roles = set()
    for pattern, role in obligation_patterns:
        if re.search(pattern, text_lower):
            matched_roles.add(role)
            
    if not matched_roles:
        for role, name in parties_dict.items():
            if name and name.lower() in text_lower:
                matched_roles.add(role.title())
            elif role.lower() in text_lower:
                matched_roles.add(role.title())
                
    if len(matched_roles) > 1:
        return "Both"
    elif len(matched_roles) == 1:
        return matched_roles.pop()
    return "Unknown"
```

---

## 5. React Frontend Document Viewer with Section Checklist
**File Location:** `frontend/src/pages/DocumentViewer.jsx`

### Description
A responsive page rendering dual-mode summaries (Extractive and Simplified) alongside a multi-tab AI panel. 
*   **Dynamic Checklist Panel**: Automatically visible for loan agreement documents, displaying all identified sections as checkable filters to allow users to generate targeted custom summaries.
*   **Resizable Split Layout**: Includes drag handles with interactive mouse/touch listeners allowing users to dynamically adjust panel widths.

### Key Code Snippets

#### A. Resizable Sidebar Component
```javascript
function AIInsightSidebar({ isOpen, onToggle, children }) {
  const [width, setWidth] = useState(420);
  const dragging = useRef(false);
  const startX   = useRef(0);
  const startW   = useRef(0);

  useEffect(() => {
    function onMove(e) {
      if (!dragging.current) return;
      const clientX = e.clientX ?? e.touches?.[0]?.clientX ?? startX.current;
      const dx  = startX.current - clientX;
      const nw  = Math.min(680, Math.max(320, startW.current + dx));
      setWidth(nw);
    }
    function onUp() { 
      dragging.current = false; 
      document.body.style.cursor = ''; 
      document.body.style.userSelect = ''; 
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',   onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup',   onUp);
    };
  }, []);

  function startDrag(e) {
    dragging.current = true;
    startX.current   = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
    startW.current   = width;
    document.body.style.cursor     = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }

  return (
    <>
      <aside
        className="fixed top-0 right-0 h-full z-20 flex flex-col bg-white border-l border-slate-200 shadow-lg"
        style={{ width, transform: isOpen ? 'translateX(0)' : 'translateX(100%)' }}
      >
        <div onMouseDown={startDrag} className="absolute left-0 top-0 h-full w-1 cursor-col-resize hover:bg-blue-200 z-10" />
        <div className="flex flex-col h-full overflow-hidden">{children}</div>
      </aside>
      <div className="shrink-0 transition-all" style={{ width: isOpen ? width : 0 }} />
    </>
  );
}
```

#### B. Section Checklist & Re-Summarization Triggers
```javascript
{showChecklist && (
  <Card className="border-blue-200 bg-blue-50/50">
    <CardContent className="p-5">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">Loan Agreement Checklist Filter</h3>
      <div className="space-y-4">
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="radio" checked={checklistMode === 'ai_decide'} onChange={() => { setChecklistMode('ai_decide'); setSelectedSections([]); }} />
            Let AI Decide (default)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="radio" checked={checklistMode === 'selected'} onChange={() => setChecklistMode('selected')} />
            Select Specific Sections
          </label>
        </div>
        
        {checklistMode === 'selected' && (
          <div className="rounded-lg border border-slate-200 bg-white p-4 max-h-48 overflow-y-auto grid grid-cols-1 sm:grid-cols-2 gap-2">
            {sections.map(s => (
              <label key={s} className="flex items-start gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={selectedSections.includes(s)} onChange={(e) => {
                  if (e.target.checked) setSelectedSections([...selectedSections, s]);
                  else setSelectedSections(selectedSections.filter(x => x !== s));
                }} />
                <span>{s}</span>
              </label>
            ))}
          </div>
        )}
        
        <button 
          disabled={summaryUpdating}
          onClick={async () => {
            try {
              setSummaryUpdating(true);
              const payloadSections = checklistMode === 'selected' ? selectedSections : [];
              await triggerCustomSummary(id, checklistMode, payloadSections);
              setTimeout(() => loadAll().finally(() => setSummaryUpdating(false)), 5000);
            } catch (e) {
              alert("Failed to start resummarization");
            }
          }}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {summaryUpdating ? 'Updating…' : 'Update Summary'}
        </button>
      </div>
    </CardContent>
  </Card>
)}
```
