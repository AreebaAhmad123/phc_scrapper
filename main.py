import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

# Centralized Configurations & Security Layer
from config import settings  

# Custom Service Modules Injections
from services.pdf_processor import download_and_convert_pdf
from services.drive_service import upload_pdf_to_drive
from services.text_splitter import prepare_chunk_payloads
from services.weaviate_service import WeaviateIngestionService
from services.rag_engine import RAGEngineService
from services.classifier import QueryClassifierService  # Injected Classifier Guard

# Explicit Data Validation Models
class IngestRequest(BaseModel):
    case_id: str
    case_title: Optional[str] = None
    source_url: Optional[str] = None

class QueryRequest(BaseModel):
    prompt: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Unified Application Lifecycle Manager - Safely boots and binds Ingestion,
    Advanced Hybrid RAG, and Domain Security Classifier Services into global memory.
    """
    print("[SYSTEM] Starting FastAPI application Stage 3 lifecycle...")
    global db_service, rag_service, classifier_service
    
    # Core Service Bootstrapping
    db_service = WeaviateIngestionService()
    rag_service = RAGEngineService()
    classifier_service = QueryClassifierService()  # Boots up the firewall engine
    
    yield 
    
    print("[SYSTEM] Shutting down application lifecycle...")
    # Safe infrastructure socket teardowns
    if 'db_service' in globals():
        db_service.close()
    if 'rag_service' in globals():
        rag_service.close()


# Initialize unified engine mount
app = FastAPI(
    title="Peshawar High Court Judgment Processing API Engine (Stage 3)",
    version="3.0.0",
    lifespan=lifespan  
)


# ─── STAGE 1: INGESTION ROUTE ENDPOINT ───
@app.post("/ingest")
def ingest_case(data: IngestRequest):
    if not data.source_url:
        raise HTTPException(status_code=400, detail="Source URL is missing!")
        
    try:
        # Incremental Ingestion Checkpost Guard
        print(f"[INCREMENTAL CHECK] Querying Weaviate index for Case ID: {data.case_id}...")
        if db_service.case_exists(data.case_id):
            print(f"[INFO] Case ID {data.case_id} already exists in Weaviate. Skipping ingestion pipeline.")
            return {
                "status": "skipped",
                "case_id": data.case_id,
                "message": "Incremental Ingestion Guard: This judgment is already embedded in the vector index.",
                "database_indexing_state": "Ignored (Duplicate)"
            }
            
        # Transform remote binary layouts
        markdown_result = download_and_convert_pdf(data.source_url, data.case_id)
        
        # Offload backups safely onto cloud storage assets
        safe_filename = "".join(c for c in data.case_id if c.isalnum() or c in ("_", "-")).rstrip()
        local_pdf_path = os.path.join("downloaded_pdfs", f"{safe_filename}.pdf")
        
        TARGET_FOLDER_ID = settings.GOOGLE_DRIVE_FOLDER_ID
        google_drive_link = upload_pdf_to_drive(local_pdf_path, folder_id=TARGET_FOLDER_ID)
        
        # Slice contextual layout matrices
        meta_bundle = {
            "case_id": data.case_id,
            "case_title": data.case_title,
            "google_drive_url": google_drive_link
        }
        processed_chunks = prepare_chunk_payloads(markdown_result, meta_bundle)
        
        # Deploy matrix arrays straight into cloud collections space
        db_service.batch_ingest_chunks(processed_chunks)
        
        return {
            "status": "success",
            "case_id": data.case_id,
            "total_chunks_indexed": len(processed_chunks),
            "google_drive_backup": google_drive_link,
            "database_indexing_state": "Completed Successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed at execution layer: {str(e)}")


# ─── STAGE 3: INTERCEPTIVE RETRIEVAL ROUTE ENDPOINT ───
@app.post("/query")
def query_knowledge_base(data: QueryRequest):
    if not data.prompt or data.prompt.strip() == "":
        raise HTTPException(status_code=400, detail="Inbound question token cannot be empty.")
        
    try:
        print(f"[ROUTING LAYER] Intercepting user prompt for classification: {data.prompt[:50]}...")
        
        # STEP 1: Query Classification Security Audit
        classification = classifier_service.classify_query(data.prompt)
        category = classification.get("category", "RELEVANT_LEGAL")
        reason = classification.get("reason", "")
        
        print(f"[SECURITY AUDIT] Query categorized as: {category}. Reason: {reason}")
        
        # STEP 2: Defend Domain Firewall Boundaries
        if category == "IRRELEVANT":
            return {
                "status": "rejected",
                "category": category,
                "reason": reason,
                "response": "This inquiry falls outside the judicial or legal domain of the Peshawar High Court records system. Please ask a law-related question.",
                "verified_citations": []
            }
            
        # STEP 3: Route Allowed/Relevant Queries to Hybrid + Reranker Engine
        rag_response = rag_service.generate_grounded_answer(data.prompt)
        
        return {
            "status": "success",
            "category": category,
            "query": data.prompt,
            "response": rag_response["answer"],
            "verified_citations": rag_response["citations"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG Inference failed on advanced runtime pipeline: {str(e)}")