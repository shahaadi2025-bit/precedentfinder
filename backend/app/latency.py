import numpy as np
from .db import conn, rows
STAGES = ["embed_ms", "retrieve_ms", "llm_ms", "crosscheck_ms", "total_ms"]
def log(question, t):
    with conn() as c:
        c.execute("INSERT INTO latency_log(question,embed_ms,retrieve_ms,llm_ms,crosscheck_ms,total_ms) VALUES(?,?,?,?,?,?)",
                  (question, *[t[s] for s in STAGES]))
def percentiles(last_n=200):
    r = rows("SELECT * FROM latency_log ORDER BY id DESC LIMIT ?", (last_n,))
    out = {"n": len(r), "stages": {}, "recent": list(reversed(r[:30]))}
    for s in STAGES:
        v = [x[s] for x in r]
        out["stages"][s] = {p: round(float(np.percentile(v, q)), 1) for p, q in (("p50", 50), ("p95", 95), ("p99", 99))} if v else {}
    return out
