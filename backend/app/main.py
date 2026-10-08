from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from . import analyze, features, latency, ml, mlplus, ops, sec_facts
from fastapi import Request
from .config import CORS_ORIGINS, ENABLE_RAG
from .db import rows
app = FastAPI(title="PrecedentFinder")
LIMITER = ops.RateLimiter(capacity=12, per_sec=0.4)
def _limit(request: Request):
    if not LIMITER.allow(request.client.host if request.client else "local"): raise HTTPException(429, "Too many requests; wait a few seconds.")
@app.middleware("http")
async def timing(request: Request, call_next):
    import time, uuid; t0 = time.perf_counter(); resp = await call_next(request)
    resp.headers["X-Request-ID"] = uuid.uuid4().hex[:12]; resp.headers["X-Process-Ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"; return resp
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"ok": True, "rag_enabled": ENABLE_RAG}

@app.get("/deals")
def deals(q: str | None = None, sector: str | None = None, date_from: str | None = None, date_to: str | None = None, min_conf: str = "medium"):
    sql, a = "SELECT * FROM deals WHERE 1=1", []
    if q: sql += " AND (target LIKE ? OR acquirer LIKE ?)"; a += [f"%{q}%", f"%{q}%"]
    if sector: sql += " AND sector=?"; a.append(sector)
    if date_from: sql += " AND ann_date>=?"; a.append(date_from)
    if date_to: sql += " AND ann_date<=?"; a.append(date_to)
    if min_conf == "high": sql += " AND confidence='high'"
    return rows(sql + " ORDER BY ann_date DESC", a)

@app.get("/sectors")
def sectors(): return [r["sector"] for r in rows("SELECT DISTINCT sector FROM deals ORDER BY sector")]
@app.get("/unparsed")
def unparsed(): return rows("SELECT * FROM unparsed")

class Q(BaseModel): question: str; k: int = 5
@app.post("/query")
def query(q: Q, request: Request):
    _limit(request)
    if not ENABLE_RAG: raise HTTPException(503, "RAG disabled on this host (RAM limits). Run the backend locally with Ollama.")
    from . import rag
    try: return rag.answer(q.question, q.k)
    except Exception as e: raise HTTPException(500, f"RAG failed: {e}")
@app.post("/index")
def index():
    if not ENABLE_RAG: raise HTTPException(503, "RAG disabled")
    from . import rag; return {"chunks_indexed": rag.index_all()}

@app.get("/latency")
def lat(last_n: int = 200): return latency.percentiles(last_n)

@app.post("/ml/train")
def train(): return ml.train()
@app.get("/ml/metrics")
def metrics(): return ml.metrics()
class P(BaseModel): sector: str; deal_value_musd: float | None = None; year: int
@app.post("/ml/predict")
def predict(p: P):
    try: return ml.predict(p.sector, p.deal_value_musd, p.year)
    except RuntimeError as e: raise HTTPException(409, str(e))

class AnalyzeReq(BaseModel):
    acquirer: str; target: str; acquirer_price: float; target_price: float
    premium_pct: float | None = None; pct_cash: float = 50.0; synergies_musd: float = 0.0
    tax_rate: float = 25.0; cost_of_debt: float = 6.0; narrative: bool = True

@app.post("/analyze")
def analyze_deal(req: AnalyzeReq, request: Request):
    _limit(request)
    errs = ops.validate_analyze(req.model_dump())
    if errs: raise HTTPException(422, "; ".join(errs))
    try: return analyze.run(req.model_dump(), with_narrative=req.narrative)
    except ValueError as e: raise HTTPException(422, str(e))
    except Exception as e: raise HTTPException(502, f"Analysis failed ({type(e).__name__}): {e}")

@app.get("/company")
def company(q: str):
    try:
        best, cands = sec_facts.resolve(q); return {"best": best, "candidates": cands}
    except ValueError as e: raise HTTPException(404, str(e))

@app.get("/stats/sectors")
def stats_sectors(): return features.sector_stats()
@app.get("/stats/trend")
def stats_trend(): return features.trend()
@app.get("/quality")
def quality(): return features.quality()
@app.get("/export/deals.csv", response_class=PlainTextResponse)
def export_deals(): return PlainTextResponse(features.export_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=precedents.csv"})
@app.post("/analyses")
def save(title: str = Body(...), payload: dict = Body(...)): return {"id": features.save_analysis(title, payload)}
@app.get("/analyses")
def analyses(): return features.list_analyses()
@app.get("/analyses/{i}")
def analysis(i: int):
    r = features.get_analysis(i)
    if r is None: raise HTTPException(404, "not found")
    return r
@app.delete("/analyses/{i}")
def del_analysis(i: int): features.delete_analysis(i); return {"ok": True}
@app.post("/report", response_class=PlainTextResponse)
def report(payload: dict = Body(...)): return PlainTextResponse(features.report_md(payload), media_type="text/markdown")

@app.get("/acquirers")
def acquirers(): return features.acquirers()
@app.get("/stats/histogram")
def histogram(): return features.histogram()
@app.get("/stats/forecast")
def forecast(): return features.forecast()
@app.get("/watchlist")
def watchlist(): return features.watch_list()
@app.post("/watchlist")
def watch_add(ticker: str = Body(...), note: str = Body("")): features.watch_add(ticker, note); return {"ok": True}
@app.delete("/watchlist/{i}")
def watch_del(i: int): features.watch_del(i); return {"ok": True}
@app.get("/compare")
def compare(a: int, b: int):
    x, y = features.get_analysis(a), features.get_analysis(b)
    if x is None or y is None: raise HTTPException(404, "analysis not found")
    return {"a": f"{x['acquirer']['ticker']}+{x['target']['ticker']}", "b": f"{y['acquirer']['ticker']}+{y['target']['ticker']}", "rows": features.compare(x, y)}
@app.get("/price")
def price(ticker: str):
    try: return features.price(ticker)
    except ValueError as e: raise HTTPException(404, str(e))
    except Exception as e: raise HTTPException(502, f"Price lookup failed ({type(e).__name__}); enter the price manually.")

@app.get("/health/deep")
def health_deep(): return ops.deep_health()
@app.get("/ml/diagnostics")
def ml_diagnostics(): return mlplus.diagnostics(ml.frame())
@app.get("/similar")
def similar(sector: str, year: int, k: int = 5):
    return mlplus.similar_deals(rows("SELECT target, acquirer, ann_date, sector, premium, premium_ref FROM deals WHERE premium IS NOT NULL"), sector, year, k)
