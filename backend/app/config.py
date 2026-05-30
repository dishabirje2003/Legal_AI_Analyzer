  
from pydantic_settings import BaseSettings, SettingsConfigDict  
  
  
class Settings(BaseSettings):  
    model_config = SettingsConfigDict(  
        env_file='.env',  
        env_file_encoding='utf-8',  
        extra='ignore',  
    )  
  
    supabase_url: str  
    supabase_service_role_key: str  
    supabase_storage_bucket: str = 'legal-documents'  
  
    frontend_origin: str | None = None  
  
    # AI / embeddings  
    embedding_model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'  
    chunk_size: int = 1000  
    chunk_overlap: int = 120  
    embedding_batch_size: int = 32  
    spacy_model: str = 'en_core_web_sm'  
    ner_max_chars: int = 100_000  
  
    # Gemini summarization  
    gemini_api_key: str | None = None  
    gemini_model_name: str = 'gemini-2.0-flash'  
    gemini_map_model_name: str = 'gemini-2.0-flash'
    gemini_reduce_model_name: str = 'gemini-2.0-flash'
    gemini_timeout_seconds: float = 120 
    gemini_max_retries: int = 3
    gemini_rate_limit_backoff_seconds: float = 20.0  
    gemini_concurrency: int = 1  
    gemini_cache_size: int = 256  
    gemini_max_chunks: int = 15  
    gemini_map_timeout_seconds: float = 60  
    gemini_map_max_retries: int = 3 
    gemini_reduce_timeout_seconds: float = 90 
    gemini_reduce_max_retries: int = 3 
    gemini_verify_timeout_seconds: float = 45
    gemini_enable_verification: bool = True
  
    # Pinecone (optional; MiniLM vectors are 384-d - index must match)  
    pinecone_api_key: str | None = None  
    pinecone_index_name: str = 'legal-doc-embeddings'  
    pinecone_host: str | None = None  
    pinecone_expected_dimension: int | None = 384  
  
  
settings = Settings()  
