import sys
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent))

from app.services.supabase_service import supabase, supabase_execute
from app.services.ai.legal_summarization import extract_sections

def test_extraction(doc_id):
    print(f"Fetching text for document: {doc_id}")
    row = supabase_execute(
        supabase.table("document_text")
        .select("extracted_text")
        .eq("document_id", doc_id)
        .limit(1)
    ).data

    text = ""
    if row and row[0].get("extracted_text"):
        text = row[0]["extracted_text"]
        print(f"✅ Text loaded successfully from DB ({len(text)} characters).")
    else:
        print("⚠️ No text in DB, checking tmp folder fallback...")
        tmp_file = Path(__file__).resolve().parent / "tmp" / f"{doc_id}.txt"
        if tmp_file.exists():
            text = tmp_file.read_text(encoding='utf-8')
            print(f"✅ Text loaded successfully from tmp folder ({len(text)} characters).")
        else:
            print("❌ No extracted text found anywhere.")
            return
    
    print("\n--- Running Section Extraction ---")
    sections = extract_sections(text)
    
    if len(sections) == 0:
        print("❌ FAILED: Found 0 sections.")
    else:
        print(f"✅ SUCCESS: Found {len(sections)} sections!\n")
        for i, s in enumerate(sections):
            content_preview = s['content'][:50].replace('\n', ' ') + "..."
            print(f"{i+1}. {s['title']}")
            print(f"   Preview: {content_preview}\n")

if __name__ == "__main__":
    # Test on your specific document
    test_extraction("4e363054-14fa-48af-aebb-3b0a386b328a")
