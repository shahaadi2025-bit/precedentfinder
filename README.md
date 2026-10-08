# PrecedentFinder
[![CI](https://github.com/shahaadi2025-bit/precedentfinder/actions/workflows/ci.yml/badge.svg)](https://github.com/shahaadi2025-bit/precedentfinder/actions/workflows/ci.yml) ![license](https://img.shields.io/badge/license-MIT-blue)

Extracts M&A precedent-transaction data from public SEC filings (EDGAR), lets you query the filings in natural language (local RAG), and estimates plausible deal premiums with a small ML model trained on the extracted data. Everything is free and local-first: no paid APIs, no signup.

## Verification status (read this first)
| Component | Evidence so far | Status |
|---|---|---|
| Regex extractor | unit tests on real filing excerpts; author ran it on 50 real DEFM14A filings (second run: 25 parsed / 19 unparsed / 6 SPACs skipped) | works on a subset; **per-field accuracy NOT yet measured** |
| EDGAR search/fetch, SIC lookup | author's local ingest run completed against live EDGAR (after fixing encoding/regex bugs it exposed) | exercised live |
| Deal math (EPS accretion, break-evens, collar) | hand-calculated unit tests | arithmetic verified; model is deliberately simplified |
| ML premium model | tested on synthetic data only; **never trained on real extracted data** | unverified |
| RAG (ChromaDB + Ollama) | unit tests for helper functions only | **never run end-to-end** |
| Deal Analyzer SEC XBRL financials | unit-tested on synthetic JSON | **never run against live SEC** |
| Frontend (Next.js) | never compiled or rendered | **unverified** |
| Deployment (Render/Vercel) | not done | **not done** |
Details and the record of what has actually been measured live in [VERIFICATION.md](VERIFICATION.md). Do not cite unverified rows as working.

## Deal Analyzer (new)
Enter an acquirer and a target (US-listed; name or ticker) plus today's share prices, an optional premium, % cash, and synergy assumption. The backend:
1. pulls each company's latest annual figures from SEC EDGAR XBRL (`data.sec.gov`, free): revenue, net income, EBITDA (operating income + D&A), cash, debt, shares;
2. builds premium scenarios from the ML model (P10/point/P90) or, if untrained, precedent quartiles, plus yours;
3. runs deterministic deal math (offer price, equity value, EV, EV/Revenue, EV/EBITDA, offer P/E, ownership split, EPS accretion/dilution for 0/50/100% cash, break-even synergies, financing need);
4. (optional, needs Ollama + `/index`) retrieves precedent-filing excerpts and has the local LLM write the strategic/valuation/risk narrative, then checks every number it cites against the computed facts.
Endpoint: `POST /analyze`. Limits: banks and foreign filers often lack the needed XBRL tags; figures are last-10-K, not live; EPS math ignores fees, purchase accounting and refinancing; the AI text is a draft to verify, not advice.

## Feature pack (v2)
New: landing page (`/`, animated SVG hero, pipeline diagram, scroll reveals, counters; respects reduced-motion) and dashboard (`/dashboard`).
Analyzer extras: break-even premium, synergy sensitivity, premium football field, percentile vs precedents, cash-on-hand case, rule-based risk flags, saved analyses, Markdown report download.
Dataset: sector and year premium charts, data-quality panel (parse rate, field coverage, flags, reject reasons), CSV export, dark mode, premium outlier/range/date-plausibility guards, `scripts/review.py` evidence + labeling template.
Endpoints: `/stats/sectors`, `/stats/trend`, `/quality`, `/export/deals.csv`, `/analyses` (+`/{id}`), `/report`.

## Feature pack 2
Compare saved analyses side by side, watchlist, acquirer history, premium distribution chart, straight-line trend projection (rough; needs 3+ years), deal search box, free share-price lookup (Stooq; manual entry as fallback), shareable `/dashboard?analysis=ID` links, Print/PDF button, and `scripts/refresh.py` (+ Windows Task Scheduler command) to pick up new proxies.

## Feature pack 3
Valuation: value-creation test (premium vs capitalized synergies, fees, payback), contribution vs ownership, relative P/E, debt capacity and optimal cash mix under a leverage cap, pro forma credit stats, exchange ratio, break-even acquirer price, fixed-ratio collar table, Monte Carlo EPS distribution, tornado sensitivity.
ML honesty tools (`/ml/diagnostics`): model comparison vs baseline, permutation importance, interval-coverage check, learning curve, biggest misses; `/similar` nearest precedent deals.
RAG: answers about extracted targets come straight from the table (no LLM), keyword re-rank over vector hits, answer cache.
Ops: rate limiting, request-ID/timing headers, input validation, 24h on-disk SEC cache, `/health/deep`, company-name normalisation.

## Architecture
```
EDGAR full-text search ──► filing HTML ──► BeautifulSoup isolates deal text
 (DEFM14A, 8-K 1.01/2.01)                      │  (cover/summary + windows around "premium", "enterprise value", "EBITDA")
                                               ▼
                         regex extractors (target, acquirer, date, value, premium, multiple)
                                    │                         │
                      confident ──► deals (SQLite)    low confidence ──► unparsed (SQLite, with reasons)
                                    │
        ┌───────────────────────────┼─────────────────────────────┐
        ▼                           ▼                             ▼
  chunks → MiniLM embeddings   RandomForest (scikit-learn)   FastAPI ──► Next.js (Tailwind, Recharts)
  → ChromaDB → Ollama LLM      premium ~ sector, size, year      deals table · query box · predictor · latency dashboard
  → numeric cross-check vs deals
  → per-stage timing → latency_log → p50/p95/p99
```

## Run locally
```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-rag.txt
export SEC_USER_AGENT="PrecedentFinder you@yourdomain.com"      # SEC requires a real contact
python -m app.ingest --start 2022-01-01 --end 2025-12-31 --forms DEFM14A 8-K --max 200   # all sectors; add --sectors Technology to narrow
ollama pull llama3.2:3b && ollama serve                          # separate terminal
uvicorn app.main:app --reload                                    # then POST /index once, POST /ml/train
# frontend
cd ../frontend && cp .env.example .env.local && npm install && npm run dev
```
Tests: `cd backend && pip install pytest && pytest tests`.

## Verification checklist (do this first)
1. Ingest ~50 filings; open the `unparsed` list in the UI and read why each was rejected.
2. Hand-label ~20 filings into `labels.csv` (`adsh,acquirer,ann_date,premium,deal_value_musd,multiple`) and run `python scripts/eval_accuracy.py labels.csv` for per-field precision/recall. Fix regexes where it misses.
3. Ask 10+ questions in the UI and confirm the cross-check badges behave sensibly.

## Free-tool choices
| Need | Choice | Why |
|---|---|---|
| Data | EDGAR full-text search | free, public, only needs a descriptive User-Agent |
| Parsing | BeautifulSoup + regex | transparent, debuggable, no model guessing |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | small, CPU-friendly, local |
| Vector store | ChromaDB (persistent, local) | no server or account |
| LLM | Ollama + Llama 3.2 3B / Phi-3-mini | local open weights |
| ML | scikit-learn RandomForest | works on small tabular data; tree spread gives a rough range |

## Extraction behavior and known limits
- Fields are extracted only from anchored patterns. If target, acquirer, announcement date, or both premium and deal value are missing, the filing goes to `unparsed` with reasons instead of being guessed.
- Premiums record what they are measured against (spot close, VWAP, unaffected). Only spot-close premiums are used to train the ML model.
- A premium whose reference date falls after the agreement date is flagged and sent to `unparsed`.
- Explicit transaction EV/EBITDA or EV/Revenue multiples are rarely stated in proxies (fairness-opinion tables mostly show comparable-company ranges). Expect few multiples, so the model predicts **premium** only.
- Deal value patterns were verified only on synthetic sentences; check them on real filings.
- Target is taken from the EDGAR filer name; sector from the target's SIC code. Acquirer relative size is not derivable from these filings, so it is not a model feature.

## ML performance and honest limitations
Numbers depend on what you ingest, so none are hardcoded. `POST /ml/train` writes `data/metrics.json` and the UI shows: held-out test MAE and R², a predict-the-mean baseline, 5-fold CV MAE ± std, per-sector test error, and feature importance. The model refuses to train below 15 usable rows. Expect noisy results: premiums are driven by deal-specific factors (bidding contests, target distress, run-ups) that this model does not see, and per-sector samples will be small. If the model does not beat the baseline, the UI says so. The prediction range is the 10th–90th percentile spread across forest trees, which is a rough spread, not a statistical confidence interval.

## Deployment
- **Frontend (Vercel):** import `frontend/`, set `NEXT_PUBLIC_API_URL` to the Render URL.
- **Backend (Render):** `render.yaml` deploys the API with `ENABLE_RAG=false`. Set `CORS_ORIGINS` to the Vercel URL. Render's free disk is ephemeral and sleeps when idle, so commit a seeded `backend/data/precedent.db` (and train the model before deploying, or call `/ml/train` after each cold start).
- **Local-LLM constraint:** torch, the embedding model and Ollama exceed free-tier RAM (512 MB), and Ollama can't run there. The hosted demo serves the table, extraction review and ML predictor; the RAG query box and latency dashboard require running the backend locally with Ollama (and `NEXT_PUBLIC_API_URL` pointing at it). The query endpoint returns a clear 503 when RAG is disabled.


## Project health
- CI (GitHub Actions) runs the backend tests and a frontend production build on every push/PR; Dependabot proposes monthly updates.
- `python backend/scripts/version_check.py` prints which feature packs are installed.
- Docker (untested): `docker compose up --build` starts the API and Ollama. `scripts/dev.ps1` starts API + frontend on Windows.
- Data (`backend/data/`) is local-only and gitignored: it holds SEC filing text, the SQLite DB, vectors and the trained model.
- **Not a financial product.** Output is illustrative, extraction can be wrong, and the model is trained on a small sample.
