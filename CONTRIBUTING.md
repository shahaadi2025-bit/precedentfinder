# Contributing
1. `cd backend && python -m venv .venv && .\.venv\Scripts\Activate.ps1 && pip install -r requirements.txt pytest && pytest tests`
2. Extraction changes need a regression test built from a short real filing sentence (see `tests/test_all.py`). Never guess: if a field can't be extracted confidently, it must stay unparsed.
3. Don't commit `backend/data/`, `.env*`, or anything with personal contact details. Set your own `SEC_USER_AGENT`.
4. Keep features free and local (no paid APIs).
