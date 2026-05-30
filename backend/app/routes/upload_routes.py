  
from __future__ import annotations  
  
import logging  
  
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile  
  
from app.models.document_model import UploadResponse  
from app.services.document_service import document_service  
from app.services.job_queue import job_queue  
from app.services.processing_service import processing_service  
from app.services.storage_service import storage_service  
from app.utils.file_utils import build_storage_path, ensure_allowed_file  
  
router = APIRouter(tags=['upload'])  
logger = logging.getLogger('upload')  
  
_TYPE_MAP = {
    'contract': 'contract',
    'contracts': 'contract',
    'court_judgment': 'court_judgment',
    'court judgment': 'court_judgment',
    'court': 'court_judgment',
    'property': 'property',
    'property_agreement': 'property',
    'insurance/financial': 'insurance/financial',
    'general_legal_document': 'general_legal_document',
    'general legal document': 'general_legal_document',
    'general': 'general_legal_document',
    'rental_contract': 'contract',
    'employment_contract': 'contract',
    'rental': 'contract',
    'employment': 'contract',
}

def normalize_document_type(raw):
    key = (raw or '').strip().lower()
    if key in _TYPE_MAP:
        return _TYPE_MAP[key]
    valid_types = ", ".join(sorted(set(_TYPE_MAP.values())))
    raise ValueError(f'Invalid document_type. Use one of: {valid_types}')
  
@router.post('/upload', response_model=UploadResponse)  
async def upload_document(background_tasks: BackgroundTasks, document_name: str = Form(None), document_type: str = Form(...), file: UploadFile = File(...), user_id: str = Form(None)):  
    try:  
        ensure_allowed_file(file.filename or '')  
    except ValueError as exc:  
        raise HTTPException(status_code=400, detail=str(exc)) from exc  
  
    content = await file.read()  
    if not content:  
        raise HTTPException(status_code=400, detail='Empty file')  
  
    try:  
        normalized_type = normalize_document_type(document_type)  
    except ValueError as exc:  
        raise HTTPException(status_code=400, detail=str(exc)) from exc  
  
    stored_name = (document_name or '').strip() or (file.filename or 'document')  
    object_path, document_id = build_storage_path(user_id, file.filename or document_name)  
  
    try:  
        stored = storage_service.upload_bytes(object_path=object_path, content=content, content_type=file.content_type)  
    except Exception as exc:  
        logger.exception('Storage upload failed')  
        raise HTTPException(status_code=502, detail='Failed to upload to storage') from exc  
  
    try:  
        document_service.insert_document(document_id=document_id, user_id=user_id, document_name=stored_name, document_type=normalized_type, file_url=stored.public_url, processing_status='uploaded')  
    except Exception as exc:  
        logger.exception('DB insert failed (documents)')  
        raise HTTPException(status_code=502, detail='Failed to insert document metadata') from exc  
  
    try:  
        job_queue.enqueue_document(document_id)  
    except Exception:  
        logger.exception('Queue enqueue failed; falling back to in-process background task')  
        background_tasks.add_task(processing_service.process_document, document_id=document_id)  
  
    return UploadResponse(document_id=document_id, file_url=stored.public_url, processing_status='uploaded')  
