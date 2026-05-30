  
from datetime import datetime  
from typing import Any, Literal, Optional  
  
from pydantic import BaseModel, ConfigDict, Field, field_validator  
  
  
DocumentType = Literal[  
    'contract',  
    'court_judgment',  
    'general_legal_document',  
    'property_agreement',  
    'rental_contract',  
    'employment_contract',  
]  
  
  
ProcessingStatus = Literal[  
    'uploaded',  
    'processed',  
    'failed',  
]  
  
  
class AnalysisSection(BaseModel):  
    title: str  
    content: str  
  
  
class DocumentOut(BaseModel):  
    model_config = ConfigDict(extra='ignore')  
  
    id: str  
    user_id: Optional[str] = None  
    document_name: Optional[str] = None  
    document_type: Optional[str] = None  
    file_url: Optional[str] = None  
    upload_date: Any = None  
    processing_status: Optional[str] = None  
    page_count: Optional[int] = None  
  
    @field_validator('id', 'user_id', mode='before')  
    @classmethod  
    def _uuid_to_str(cls, v):  
        return str(v) if v is not None else None  
  
  
class DocumentTextOut(BaseModel):  
    document_id: str  
    extracted_text: str  
    extraction_method: Optional[str] = None  
  
  
class UploadResponse(BaseModel):  
    document_id: str  
    file_url: str  
    processing_status: str  
  
  
class DocumentAnalysisOut(BaseModel):  
    document_id: str  
    extractive_summary: Optional[str] = None  
    extractive_bullets: list[str] = Field(default_factory=list)  
    abstractive_summary: Optional[str] = None  
    structured_sections: list[AnalysisSection] = Field(default_factory=list)  
    resolved_document_type: Optional[str] = None  
    detected_contract_subtype: Optional[str] = None  
    entities: Any = None  
