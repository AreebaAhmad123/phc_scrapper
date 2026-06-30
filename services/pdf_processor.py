import os
import time
import fitz  # PyMuPDF
import requests

def download_and_convert_pdf(pdf_url: str, case_id: str) -> str:
    """
    Downloads a PDF from a remote URL locally and converts its content 
    into a structured Markdown string.
    """
    # 1. Setup local temporary storage directory
    download_dir = "downloaded_pdfs"
    os.makedirs(download_dir, exist_ok=True)
    
    # Clean case_id to make a safe filename
    safe_filename = "".join(c for c in case_id if c.isalnum() or c in ("_", "-")).rstrip()
    pdf_path = os.path.join(download_dir, f"{safe_filename}.pdf")
    
    print(f"[{time.strftime('%X')}] Starting download for Case ID {case_id}...")
    
    # 2. Download the binary stream safely
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()  # Throws error if 404 or 500
    
    with open(pdf_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    print(f"[{time.strftime('%X')}] PDF successfully saved to disk: {pdf_path}")
    
    # 3. Extract text and structure it into Markdown (.md)
    print(f"[{time.strftime('%X')}] Extracting text data using PyMuPDF...")
    doc = fitz.open(pdf_path)
    
    # Document header metadata block
    markdown_content = f"# Judgment Document Layout\n"
    markdown_content += f"**Source Case Identifier:** {case_id}\n"
    markdown_content += f"**Total Pages Processed:** {len(doc)}\n\n"
    markdown_content += "---\n\n"
    
    # Loop through each page and extract content sequences
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        page_text = page.get_text("text")  # Extracts clean continuous text block
        
        markdown_content += f"## Page {page_num + 1}\n\n"
        markdown_content += f"{page_text}\n\n"
        markdown_content += "---\n\n"
        
    doc.close()
    print(f"[{time.strftime('%X')}] PDF text successfully parsed into Markdown layout.")
    
    # We return the compiled markdown string back to the pipeline controller
    return markdown_content