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

# Decisions & Evaluation Metrics - Stage 3 Advanced Retrieval

This document outlines the experiments, architectural evaluations, and incremental improvements tracking from Stage 2 (Vector Baseline) to Stage 3 (Advanced Search System).

## Evaluation Setup & Metrics Matrix
* **Dataset Size:** 15 Hand-authored Ground-Truth Judicial Evaluation Pairs (`eval_set.json`).
* **Primary Metric Measured:** **Hit Rate @ Top-3** (Does the correct context block appear in the top 3 retrieved results?).

| Retrieval Strategy | Hit Rate @ 3 (Score) | Average Latency | Status / Observations |
| :--- | :---: | :---: | :--- |
| **Stage 2 Baseline** (Vector Only) | **73.3%** (11/15) | ~45ms | Fast, but misses exact string matches like "2026 PHC 153" due to vector density smoothing. |
| **Hybrid Search** (Dense Vector + BM25 Keyword) | **86.6%** (13/15) | ~54ms | Successfully resolved token mismatches. Aligned numerical citations perfectly by weighting term occurrences. |
| **Optimized Pipeline** (Hybrid + Cross-Encoder Reranker) | **93.3%** (14/15) | ~89ms | Cross-attention deep scoring pushed obscure chunks from lower ranks (e.g., Rank #6) directly into Top-3. |

---

##  Query Classification Matrix
We defend the definition of "Irrelevant Content" as any inbound request that does not target:
1. Judicial precedents, case citations, high court operations, or constitutional legal interpretations.
2. Administrative procedural rules or legal definitions relevant to Pakistani jurisprudence.

All off-domain parameters (e.g., general knowledge, math, coding, creative writing) are caught by the firewall block and rejected at the routing layer without exhausting database connection streams.

---

## Honest Reporting & Analytical Insights
1. **The Keyword Advantage:** Shifting to Hybrid Search directly solved the failure modes of pure dense vectors when handling unique alphanumeric sequence tokens like case numbers (`TEST_CASE_002`, `W.P. 1234/2025`).
2. **Reranker Impact:** The Cross-Encoder effectively mitigated token alignment flaws by calculating query-document cross-attention, capturing semantic transitions that bi-encoders smooth out.
3. **The 1 Missing Query Negative Result:** Query `EVAL_005` remained missing across all strategies due to a literal text layer typo within the underlying processed sample document block. Reranking cannot fix structural lexical anomalies if the text anchor itself is corrupted.