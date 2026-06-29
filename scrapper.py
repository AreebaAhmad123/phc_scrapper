import os
import json
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

TARGET_YEAR = "2025"
SEARCH_URL = "https://www.peshawarhighcourt.gov.pk/PHCCMS/reportedJudgments.php?action=search"
BASE_URL = "https://www.peshawarhighcourt.gov.pk/PHCCMS/"
PDF_DIR = "downloaded_pdfs"
OUTPUT_JSON = f"judgments_{TARGET_YEAR}.json"
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_date_to_iso(date_str):
    """Converts local date formats into standard ISO 8601 (YYYY-MM-DD) string."""
    if not date_str or "awaited" in date_str.lower():
        return None
    
    # Try parsing common formats like DD/MM/YYYY or DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str.strip()

def load_existing_records():
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {record["id"]: record for record in data}, data
        except json.JSONDecodeError:
            print("Warning: Existing JSON file was corrupted. Starting fresh.")
    return {}, []

def fetch_html_for_year(target_year):
    payload = {
        "year": str(target_year),       
        "judge": "0",                   
        "category": "0",                
        "txtsearchbyremarks": "",       
        "submit": "search"            
    }
    
    timeout_seconds = 35 
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"[{time.strftime('%X')}] (Attempt {attempt}/{MAX_RETRIES}) Sending form request for year {target_year}...")
            response = requests.post(SEARCH_URL, data=payload, headers=HEADERS, timeout=timeout_seconds)
            response.raise_for_status()
            return response.text
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            print(f"   Network issue on attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                sleep_time = attempt * 5  
                print(f"   Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
            else:
                print("   Error: Max retries reached. Server is currently down or unresponsive.")
        except requests.exceptions.RequestException as e:
            print(f"   Critical request failure: {e}")
            break
    return None

def download_pdf(relative_pdf_url):
    if not relative_pdf_url:
        return None
        
    os.makedirs(PDF_DIR, exist_ok=True)
    full_pdf_url = BASE_URL + relative_pdf_url
    filename = relative_pdf_url.split("/")[-1]
    local_path = os.path.join(PDF_DIR, filename)
    
    if os.path.exists(local_path):
        print(f"   -> Skipping download: {filename} already exists locally.")
        return local_path

    try:
        time.sleep(1.5)  # Throttling to respect site etiquette
        response = requests.get(full_pdf_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        with open(local_path, "wb") as f:
            f.write(response.content)
        print(f"   -> Downloaded file successfully: {filename}")
        return local_path
    except Exception as e:
        print(f"   -> Download failed for file ({filename}): {e}")
        return None

def parse_and_process():
    existing_records_dict, all_records_list = load_existing_records()
    initial_count = len(all_records_list)
    
    html_data = fetch_html_for_year(TARGET_YEAR)
    if not html_data:
        print("Error: Could not retrieve page source from the server.")
        return

    soup = BeautifulSoup(html_data, "html.parser")
    table = soup.find("table", id="employee_list")
    
    if not table:
        print(f"Notice: Form connected, but no results table layout was found for year {TARGET_YEAR}.")
        return

    rows = table.find_all("tr")
    new_records_added = 0

    print("Target data grid found. Parsing layout rows...")
    
    for row in rows:
        cells = row.find_all("td")
        if not cells or len(cells) < 9:
            continue  
            
        raw_sr_no = cells[0].text.strip()
        case_info = cells[1].text.strip()
        remarks = cells[2].text.strip()
        other_citation = cells[3].text.strip()
        neutral_citation = cells[4].text.strip()
        raw_date = cells[5].text.strip()
        sc_status = cells[6].text.strip()
        category = cells[7].text.strip()
        
        pdf_anchor = cells[8].find("a")
        relative_link = pdf_anchor['href'] if pdf_anchor and pdf_anchor.has_attr('href') else None
        
        judgment_id = f"PHC_{TARGET_YEAR}_{raw_sr_no}"
        
        if judgment_id in existing_records_dict:
            continue

        if not relative_link or relative_link.strip() == "":
            print(f"Skipping record #{raw_sr_no}: No downloadable PDF link attached.")
            continue

        print(f"\nProcessing record #{raw_sr_no}: {case_info[:40]}...")
        saved_file_path = download_pdf(relative_link)
        
        # Robust Schema Conversion
        record = {
            "id": judgment_id,
            "serial_no": int(raw_sr_no),  # Converted to Integer
            "case_info": case_info,
            "remarks": remarks,
            "other_citation": other_citation,
            "neutral_citation": neutral_citation,
            "decision_date": clean_date_to_iso(raw_date),  # Converted to ISO 8601 (YYYY-MM-DD)
            "sc_status": sc_status,
            "category": category,
            "remote_pdf_url": BASE_URL + relative_link if relative_link else None,
            "local_pdf_path": saved_file_path
        }
        
        all_records_list.append(record)
        existing_records_dict[judgment_id] = record
        new_records_added += 1

    if new_records_added > 0:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(all_records_list, f, indent=4, ensure_ascii=False)
    
    print("\nStage Complete")
    print(f"Previous local data points found: {initial_count}")
    print(f"New unique records scraped and stored: {new_records_added}")
    print(f"Total entries currently monitored: {len(all_records_list)}")

if __name__ == "__main__":
    parse_and_process()