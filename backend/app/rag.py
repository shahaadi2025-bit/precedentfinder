"""Stage 2: chunk -> local embeddings -> Chroma -> Ollama, with numeric cross-check against the deals table and per-stage timing."""
import re, time, requests
from . import latency, ragplus
from .config import TEXTS, CHROMA_DIR, EMBED_MODEL, OLLAMA_URL, OLLAMA_MODEL
from .db import rows
_m = {}
def _model():
    if "m" not in _m:
        from sentence_transformers import SentenceTransformer
        _m["m"] = SentenceTransformer(EMBED_MODEL)
    return _m["m"]
def _col():
    if "c" not in _m:
        import chromadb
        _m["c"] = chromadb.PersistentClient(path=str(CHROMA_DIR)).get_or_create_collection("filings", metadata={"hnsw:space": "cosine"})
    return _m["c"]

def chunk(text, size=1200, overlap=200):
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i + size]); i += size - overlap
    return out

def index_all():
    meta = {r["adsh"]: r for r in rows("SELECT adsh,target,acquirer FROM deals")}
    n = 0
    for f in TEXTS.glob("*.txt"):
        adsh = f.stem
        if adsh not in meta: continue                      # index parsed deals only
        cs = chunk(f.read_text()); embs = _model().encode(cs, batch_size=32).tolist()
        _col().upsert(ids=[f"{adsh}-{i}" for i in range(len(cs))], documents=cs, embeddings=embs,
                      metadatas=[{"adsh": adsh, "target": meta[adsh]["target"], "acquirer": meta[adsh]["acquirer"] or ""}] * len(cs))
        n += len(cs)
    return n

NUM = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(million|billion|bn|m)?|(\d+(?:\.\d+)?)\s?%|(\d+(?:\.\d+)?)x", re.I)
def extract_numbers(ans):
    res = []
    for m in NUM.finditer(ans):
        if m.group(3): res.append(("pct", float(m.group(3)), m.group(0)))
        elif m.group(4): res.append(("multiple", float(m.group(4)), m.group(0)))
        else:
            v = float(m.group(1).replace(",", "")); u = (m.group(2) or "").lower()
            if u in ("billion", "bn"): res.append(("usd_m", v * 1000, m.group(0)))
            elif u in ("million", "m"): res.append(("usd_m", v, m.group(0)))
            else: res.append(("usd", v, m.group(0)))
    return res

def check_numbers(answer, context, known):
    """known: {"pct": [...], "multiple": [...], "usd_m": [...], "usd": [...]} -> per-number status."""
    close = lambda a, b: abs(a - b) <= max(0.06, 0.005 * abs(b))
    out = []
    for kind, val, raw in extract_numbers(answer):
        if any(close(val, k) for k in known.get(kind, [])): status = "table_match"
        elif raw.replace(" ", "") in context.replace(" ", "") or re.search(re.escape(f"{val:g}"), context): status = "in_source_text_only"
        else: status = "unverified"
        out.append({"value": raw.strip(), "status": status, "flag": status != "table_match"})
    return out

def crosscheck(answer, context, deals):
    known = {"pct": [d["premium"] for d in deals if d["premium"] is not None],
             "multiple": [d["multiple"] for d in deals if d["multiple"] is not None],
             "usd_m": [d["deal_value_musd"] for d in deals if d["deal_value_musd"] is not None],
             "usd": [d["price_per_share"] for d in deals if d["price_per_share"] is not None]}
    return check_numbers(answer, context, known)

def retrieve_context(question, k=5):
    q_emb = _model().encode([question]).tolist(); res = _col().query(query_embeddings=q_emb, n_results=k)
    return res["documents"][0], res["metadatas"][0]

def generate(prompt, temperature=0.2):
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": temperature}}, timeout=300); r.raise_for_status()
    return r.json()["response"].strip()

def answer(question, k=5):
    t = {}; t0 = time.perf_counter()
    routed = ragplus.route_question(question, rows("SELECT * FROM deals"))
    if routed:
        return {"answer": routed["answer"], "number_checks": [], "any_flagged": False, "sources": [{"target": x, "adsh": "", "excerpt": "structured table"} for x in routed["deals"]],
                "timings_ms": {"total_ms": round((time.perf_counter() - t0) * 1000, 1)}, "routed": True}
    hit = ragplus.cache_get(question)
    if hit: return {**hit, "cached": True}
    q_emb = _model().encode([question]).tolist(); t["embed_ms"] = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter(); res = _col().query(query_embeddings=q_emb, n_results=k)
    docs, metas = ragplus.keyword_rerank(question, res["documents"][0], res["metadatas"][0]); t["retrieve_ms"] = (time.perf_counter() - t1) * 1000
    ctx = "\n\n".join(f"[{i+1}] ({m['target']}) {d}" for i, (d, m) in enumerate(zip(docs, metas)))
    prompt = ("Answer ONLY from the excerpts of SEC merger filings below. If they don't contain the answer, say so. "
              "Cite excerpt numbers like [1]. Quote figures exactly.\n\n" + ctx + f"\n\nQuestion: {question}\nAnswer:")
    t2 = time.perf_counter()
    r = requests.post(f"{OLLAMA_URL}/api/generate", json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.1}}, timeout=300); r.raise_for_status()
    ans = r.json()["response"].strip(); t["llm_ms"] = (time.perf_counter() - t2) * 1000
    t3 = time.perf_counter()
    names = {m["target"] for m in metas}
    deals = rows("SELECT * FROM deals")
    deals = [d for d in deals if d["target"] in names] or deals
    checks = crosscheck(ans, ctx, deals); t["crosscheck_ms"] = (time.perf_counter() - t3) * 1000
    t["total_ms"] = (time.perf_counter() - t0) * 1000; latency.log(question, t)
    out = {"answer": ans, "number_checks": checks, "any_flagged": any(c["flag"] for c in checks),
           "sources": [{"target": m["target"], "adsh": m["adsh"], "excerpt": d[:300]} for d, m in zip(docs, metas)],
           "timings_ms": {k_: round(v, 1) for k_, v in t.items()}}
    ragplus.cache_put(question, out); return out
