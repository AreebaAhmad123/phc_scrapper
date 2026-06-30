import time
from typing import List, Dict, Any

def chunk_markdown_text(markdown_text: str, chunk_size: int = 600, chunk_overlap: int = 120) -> List[str]:
    """
    Splits a long markdown string into smaller, overlapping text slices
    using a standard sliding window approach.
    """
    chunks = []
    start_idx = 0
    text_length = len(markdown_text)
    
    # If the text is already smaller than chunk_size, return it as a single chunk
    if text_length <= chunk_size:
        return [markdown_text]
        
    while start_idx < text_length:
        # Define the end boundary of the current window
        end_idx = start_idx + chunk_size
        
        # Grab the raw slice
        chunk = markdown_text[start_idx:end_idx]
        
        # Smart boundary alignment: Try not to cut a word or sentence mid-way if possible
        if end_idx < text_length:
            last_space = chunk.rfind(' ')
            if last_space != -1 and last_space > (chunk_size * 0.8):
                end_idx = start_idx + last_space
                chunk = markdown_text[start_idx:end_idx]
                
        chunks.append(chunk.strip())
        
        # Shift the window forward by subtracting the overlap
        start_idx = end_idx - chunk_overlap
        
        # Fail-safe check to prevent infinite loops if overlap calculations mismatch
        if end_idx >= text_length:
            break
            
    return chunks

def prepare_chunk_payloads(markdown_text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Takes the compiled markdown string, slices it into chunks, and packages 
    each chunk with its corresponding judicial metadata payload.
    """
    print(f"[{time.strftime('%X')}] Initializing sliding-window chunking sequence...")
    
    # 1. Break down the text string into slices
    raw_chunks = chunk_markdown_text(markdown_text, chunk_size=600, chunk_overlap=120)
    
    payloads = []
    
    # 2. Map metadata objects with each text chunk safely
    for idx, chunk_text in enumerate(raw_chunks):
        chunk_payload = {
            "chunk_id": f"{metadata['case_id']}_chunk_{idx}",
            "case_id": metadata["case_id"],
            "case_title": metadata.get("case_title", "N/A"),
            "google_drive_url": metadata.get("google_drive_url", ""),
            "text_content": chunk_text,  
            "chunk_index": idx
        }
        payloads.append(chunk_payload)
        
    print(f"[{time.strftime('%X')}] Successfully generated {len(payloads)} metadata-aligned chunks.")
    return payloads