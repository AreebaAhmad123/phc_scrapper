# Scraping Architecture Decisions

## 1. Request Handling Strategy
* **Approach Chosen:** Using `requests.post()` targeting the form endpoint `?action=search`.
* **Reasoning:** Instead of launching a heavy headless browser setup (like Selenium), the script directly sends network payloads. This bypasses the visual rendering layer, cutting CPU/RAM usage to a fraction while handling thousands of judicial index rows instantly.

## 2. Robustness and Fault-Tolerance
* **Timeout Mitigation:** Server processing on government nodes can face latency bottlenecks. The scraper extends response waiting sessions defensively to 35 seconds to prevent early socket drops.
* **Retry Strategy:** Implements an exponential backoff retry loop (maximum 3 attempts). If network faults occur, the script logs the state and pauses sequentially (5 seconds, then 10 seconds) before retrying to prevent system termination.

## 3. Ethics & Site Etiquette
* **Throttling:** Includes an explicit 1.5-second time delay (`time.sleep`) before processing individual binary stream downloads. This guarantees the pipeline respects the destination node's bandwidth boundaries.
* **Duplicate Protection:** Leverages pre-loaded memory state dictionaries and `os.path.exists()` validations to verify files locally before running network downloads.

## 4. Scheduling & Automation
* **Approach Chosen:** `APScheduler` (using `BlockingScheduler`).
* **Reasoning:** Runs on pure Python, providing native execution across Windows and Linux environments without the OS constraints of standard `cron`. It removes complex message-queue dependencies required by platforms like `Celery Beat`.

## 5. Robust Schema Design
* **Primary Key (`id`):** Formatted as a string (`PHC_YEAR_SERIAL`) to create a unique indexing signature.
* **Serial Number (`serial_no`):** Explicitly cast to an **Integer** to allow proper numeric sorting and numerical range queries in database engines.
* **Temporal Tracking (`decision_date`):** Parsed and standardized into **ISO 8601 format (YYYY-MM-DD)**. This enforces uniformity across historical entries and resolves varied string formats into clean date-time indices. Unresolved or awaited filings default to `null`.