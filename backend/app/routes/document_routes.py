  
from __future__ import annotations  
  
import json  
import logging  
import re  
from pathlib import Path  
from typing import Optional  

from fastapi import APIRouter, HTTPException, Query, Response, BackgroundTasks  
from pydantic import BaseModel

from app.models.document_model import DocumentAnalysisOut, DocumentOut, DocumentTextOut  
from app.services.document_service import document_service  
from app.services.job_queue import job_queue  
  
router = APIRouter(tags=['documents'])  
logger = logging.getLogger(__name__)  
  
def _coerce_entities(val):  
    if val is None:  
        return None  
    if isinstance(val, (dict, list)):  
        return val  
    if isinstance(val, str):  
        try:  
            return json.loads(val)  
        except json.JSONDecodeError:  
            return {'raw': val}  
    return val  
  
def _extractive_bullets(text, entities=None):  
    if isinstance(entities, dict):  
        saved = entities.get('extractive_sentences') or []  
        if isinstance(saved, list):  
            bullets = [str(item).strip() for item in saved if str(item).strip()]  
            if bullets:  
                return bullets[:12]  
    if not text or not str(text).strip():  
        return []  
    parts = [p.strip() for p in re.split(r'[.!?]\s+', str(text).strip()) if p.strip()]  
    return parts[:12]  
  
@router.delete('/documents/{document_id}', status_code=204)  
def delete_document(document_id: str):  
    deleted = document_service.delete_document_cascade(document_id=document_id)  
    if not deleted:  
        raise HTTPException(status_code=404, detail='Document not found')  
    return Response(status_code=204)  
  
@router.get('/documents', response_model=list[DocumentOut])  
def list_documents(user_id: Optional[str] = Query(default=None, description='Optional filter until auth is added'), limit: int = Query(default=200, ge=1, le=500)):  
    return document_service.list_documents(user_id=user_id, limit=limit)  
  
@router.get('/documents/{document_id}', response_model=DocumentOut)  
def get_document(document_id: str):  
    try:  
        doc = document_service.get_document(document_id=document_id)  
        if not doc:  
            raise HTTPException(status_code=404, detail='Document not found')  
        page_count = document_service.get_page_count(document_id=document_id)  
        return {**doc, 'page_count': page_count}  
    except HTTPException:  
        raise  
    except Exception as exc:  
        logger.exception('get_document failed for %s', document_id)  
        raise HTTPException(status_code=500, detail='Failed to load document') from exc 
  
@router.get('/documents/{document_id}/analysis', response_model=DocumentAnalysisOut)  
def get_document_analysis(document_id: str):  
    try:  
        doc = document_service.get_document(document_id=document_id)  
        if not doc:  
            raise HTTPException(status_code=404, detail='Document not found')  
        row = document_service.get_analysis(document_id=document_id)  
        if not row:  
            return DocumentAnalysisOut(document_id=document_id)  
        ext = row.get('extractive_summary')  
        if ext is not None and not isinstance(ext, str):  
            ext = str(ext)  
        abs_s = row.get('abstractive_summary')  
        if abs_s is not None and not isinstance(abs_s, str):  
            abs_s = str(abs_s)  
        entities = _coerce_entities(row.get('entities'))  
        structured_sections = []  
        resolved_document_type = None  
        detected_contract_subtype = None  
        if isinstance(entities, dict):  
            structured_sections = entities.get('structured_sections') or []  
            resolved_document_type = entities.get('resolved_document_type')  
            detected_contract_subtype = entities.get('detected_contract_subtype')  
        return DocumentAnalysisOut(document_id=document_id, extractive_summary=ext, extractive_bullets=_extractive_bullets(ext, entities), abstractive_summary=abs_s, structured_sections=structured_sections, resolved_document_type=resolved_document_type, detected_contract_subtype=detected_contract_subtype, entities=entities)  
    except HTTPException:  
        raise  
    except Exception:  
        logger.exception('get_document_analysis failed for %s', document_id)  
        return DocumentAnalysisOut(document_id=document_id)  
  
@router.get('/documents/{document_id}/clauses')
def get_document_clauses(document_id: str):
    try:
        from app.services.supabase_service import supabase, supabase_execute
        from app.services.ai.clause_detection_service import _build_insight_groups

        doc = document_service.get_document(document_id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')

        row = supabase_execute(
            supabase.table("document_clauses")
            .select("*")
            .eq("document_id", document_id)
            .limit(1)
        ).data

        if not row:
            return {"clauses": [], "insight_groups": []}

        clauses = row[0].get("clauses") or []

        # Always regenerate insight groups live from the raw clauses using the
        # latest grouping logic — fixes stale cached groups without re-upload.
        # Pure Python, no AI calls, so it is fast.
        insight_groups = []
        if clauses:
            try:
                insight_groups = _build_insight_groups(clauses)
                logger.info(
                    "Live insight groups for %s: %d clauses -> %d groups",
                    document_id, len(clauses), len(insight_groups)
                )
            except Exception as grp_exc:
                logger.warning("Insight grouping failed for %s: %s", document_id, grp_exc)
                insight_groups = []

        return {"clauses": clauses, "insight_groups": insight_groups}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('get_document_clauses failed for %s', document_id)
        raise HTTPException(status_code=500, detail='Failed to load document clauses') from exc

@router.get('/documents/{document_id}/risks')
def get_document_risks(document_id: str):
    try:
        from app.services.supabase_service import supabase, supabase_execute
        doc = document_service.get_document(document_id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail='Document not found')
        
        row = supabase_execute(
            supabase.table("document_risks")
            .select("risks")
            .eq("document_id", document_id)
            .limit(1)
        ).data
        
        if row and row[0].get("risks"):
            return row[0].get("risks")
        return []
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('get_document_risks failed for %s', document_id)
        raise HTTPException(status_code=500, detail='Failed to load document risks') from exc

@router.get('/documents/{document_id}/text', response_model=DocumentTextOut)  
def get_document_text(document_id: str):  
    try:  
        doc = document_service.get_document(document_id=document_id)  
        if not doc:  
            raise HTTPException(status_code=404, detail='Document not found')  
        extracted = document_service.get_extracted_text(document_id=document_id)  
        if extracted and extracted.get('extracted_text'):  
            return DocumentTextOut(document_id=document_id, extracted_text=extracted['extracted_text'], extraction_method=extracted.get('extraction_method'))  
        tmp_candidates = [  
            Path(__file__).resolve().parents[1] / 'tmp' / f'{document_id}.txt',  
            Path(__file__).resolve().parents[2] / 'tmp' / f'{document_id}.txt',  
        ]  
        for tmp_file in tmp_candidates:  
            if tmp_file.exists():  
                try:  
                    body = tmp_file.read_text(encoding='utf-8')  
                except UnicodeDecodeError:  
                    body = tmp_file.read_text(encoding='utf-8', errors='replace')  
                return DocumentTextOut(document_id=document_id, extracted_text=body, extraction_method=None)  
        return DocumentTextOut(document_id=document_id, extracted_text='', extraction_method=None)  
    except HTTPException:  
        raise  
    except Exception:  
        logger.exception('get_document_text failed for %s', document_id)  
        return DocumentTextOut(document_id=document_id, extracted_text='', extraction_method=None) 
  
class AskRequest(BaseModel):
    question: str

@router.post('/documents/{document_id}/ask')
def ask_document_question(document_id: str, req: AskRequest):
    try:
        from app.services.ai.rag_service import query_rag
        return query_rag(document_id, req.question)
    except Exception as exc:
        logger.exception("Failed to query document")
        raise HTTPException(status_code=500, detail="Failed to query document")

@router.get('/admin/queue-status')  
def get_queue_status():  
    try:  
        return job_queue.get_status()  
    except Exception as exc:  
        logger.exception('get_queue_status failed')  
        raise HTTPException(status_code=500, detail='Failed to load queue status') from exc  

class SummarizeRequest(BaseModel):
    checklist_mode: str = "ai_decide"
    selected_sections: list[str] = []

@router.get('/documents/{document_id}/sections')
def get_document_sections(document_id: str):
    doc = document_service.get_document(document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    extracted = document_service.get_extracted_text(document_id=document_id)
    text = extracted.get('extracted_text', '') if extracted else ''
    
    if not text:
        from pathlib import Path
        tmp_candidates = [
            Path(__file__).resolve().parents[1] / 'tmp' / f'{document_id}.txt',
            Path(__file__).resolve().parents[2] / 'tmp' / f'{document_id}.txt',
        ]
        for tmp_file in tmp_candidates:
            if tmp_file.exists():
                try:
                    text = tmp_file.read_text(encoding='utf-8')
                except UnicodeDecodeError:
                    text = tmp_file.read_text(encoding='utf-8', errors='replace')
                break

    from app.services.ai.legal_summarization import extract_sections
    
    sections = extract_sections(text)
    if len(sections) == 0:
        return {"sections": []}
        
    return {"sections": [s['title'] for s in sections]}

@router.post('/documents/{document_id}/summarize')
def trigger_custom_summary(document_id: str, req: SummarizeRequest, background_tasks: BackgroundTasks):
    doc = document_service.get_document(document_id=document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    from app.services.ai.pipeline import ai_pipeline
    
    def run_re_summary():
        try:
            ai_pipeline.re_summarize_document(document_id, req.selected_sections, req.checklist_mode)
        except Exception as e:
            logger.exception("Failed to resummarize document %s", document_id)
        finally:
            from app.services.supabase_service import supabase, supabase_execute
            try:
                supabase_execute(supabase.table('documents').update({'processing_status': 'analyzed'}).eq('id', document_id))
            except Exception:
                pass
            
    background_tasks.add_task(run_re_summary)
    
    # Update processing status so frontend knows to poll
    from app.services.supabase_service import supabase, supabase_execute
    try:
        supabase_execute(supabase.table('documents').update({'processing_status': 'processing'}).eq('id', document_id))
    except Exception:
        pass
    
    return {"message": "Resummarization started"}
