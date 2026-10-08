# Verification log
Fill this in from real runs. Leave blank what you have not run. Nothing here is pre-filled with results.

## Environment
- Date / commit: 
- `python backend/scripts/version_check.py`: 
- `pytest tests` result: 

## 1. Ingest (live EDGAR)
Command: `python -m app.ingest --start 2022-01-01 --end 2025-12-31 --forms DEFM14A --max 50`
- parsed / unparsed / skipped_spac / error: 
- Top rejection reasons (`scripts/diag.py`): 

## 2. Hand-labelled accuracy (the number that matters)
Procedure: `python scripts/review.py --n 25`, open each filing URL, fill the blank label columns in `labels_template.csv` **from the filing**, set `labeled=Y`, then `python scripts/eval_accuracy.py labels_template.csv`.
| Field | Labeled n | Precision | Recall |
|---|---|---|---|
| acquirer | | | |
| ann_date | | | |
| premium | | | |
| deal_value_musd | | | |
Known wrong extractions found (target, field, extracted vs correct): 

## 3. ML on real data
- `POST /ml/train` metrics (n, test MAE, R2, baseline MAE): 
- `GET /ml/diagnostics` summary (does any model beat the baseline? interval coverage?): 

## 4. RAG end-to-end
- `POST /index` chunks: 
- 10 questions asked; wrong/ungrounded answers: 
- Ollama model used / latency p50, p95: 

## 5. Deal Analyzer (live SEC XBRL)
- Pairs tried, failures (banks/foreign filers/missing tags): 

## 6. Frontend
- `npm run build` result: 
- Rendered against a live backend (which pages worked): 

## 7. Deployment
- Backend URL / frontend URL / what works there: 
