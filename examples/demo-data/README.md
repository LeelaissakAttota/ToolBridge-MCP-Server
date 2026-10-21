# ToolBridge demo data (fictional)

All data here is made up for demos and manual tests. No real customers, books or people.

| Path | What it is |
|---|---|
| `csv/cafe_orders.csv` | 40 cafe orders (4 Bengaluru branches). Rows ORD-1007 and ORD-1023 have **missing ratings** on purpose. |
| `csv/training_scores.csv` | 15 trainee scores across 3 courses. |
| `csv/empty_file.csv` | 0-byte file, used by error test E04. |
| `sql/demo_library.db` | SQLite with `books` (8 rows) and `loans` (10 rows, some not returned). |
| `text/customer_feedback.txt`, `text/meeting_notes.txt` | Input text for `llm_analysis` (already embedded in requests 11 and 12). |
| `requests/01-12_*.json` | Normal MCP requests (should succeed). |
| `requests/E01-E10_*.json` | Error requests (should be rejected safely). |
| `send.ps1` | Sends the requests and prints PASS / FAIL. |

## Start the API with the demo data (PowerShell, repo root)

```powershell
$env:TOOLBRIDGE_PHASE5__CSV_ANALYSIS__ROOT_DIRECTORY = "examples/demo-data/csv"
$env:TOOLBRIDGE_PHASE5__SQL_QUERY__DATABASE_ROOT = "examples/demo-data/sql"
$env:TOOLBRIDGE_PHASE5__SQL_QUERY__DATABASE_PATH = "demo_library.db"
.\.venv\Scripts\python.exe -m uvicorn toolbridge.main:app --host 127.0.0.1 --port 8000
```

Second terminal:

```powershell
cd examples\demo-data
.\send.ps1                  # everything
.\send.ps1 -Filter "E*"     # only error cases
.\send.ps1 -Filter 04_csv_cafe_orders -ShowBody
```

Dashboard (no password): `.\.venv\Scripts\python.exe -m streamlit run toolbridge/dashboard/app.py --server.address 127.0.0.1 --server.port 8501`

## Request list

| ID | Tool | Expected |
|---|---|---|
| 01 | initialize | success |
| 02 | tools/list | 7 tools incl. `llm_analysis` |
| 03 | system_status | success |
| 04 | csv_analysis cafe_orders.csv | 40 rows, rating missing_count = 2 |
| 05 | csv_analysis training_scores.csv | 15 rows |
| 06 | sql_query books by genre | success |
| 07 | sql_query open loans (JOIN) | success |
| 08 | stock_price AAPL | needs internet |
| 09 | currency_converter 100 USD -> INR, EUR | needs internet |
| 10 | website_reader https://example.com | needs internet |
| 11 | llm_analysis analyze feedback | needs LLM provider key |
| 12 | llm_analysis summarize notes | needs LLM provider key |
| E01 | sql_query DELETE | rejected (read-only) |
| E02 | csv_analysis `../../../.env` | rejected (path traversal) |
| E03 | csv_analysis missing file | not found |
| E04 | csv_analysis empty file | rejected (empty) |
| E05 | website_reader http:// URL | rejected (HTTPS only) |
| E06 | website_reader private IP | rejected (private address) |
| E07 | stock_price `AAPL$$` | validation error |
| E08 | currency_converter source `US` | validation error |
| E09 | llm_analysis operation `translate` | validation error |
| E10 | unknown tool | error |

Docker: the container uses the default `data/` folder. Test the demo data locally (above), not in Docker.
