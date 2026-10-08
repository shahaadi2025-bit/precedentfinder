"""Operational helpers: rate limiting, on-disk cache, input validation, name normalisation, deep health."""
import hashlib, json, re, time, os
from .config import DATA, OLLAMA_URL, MODEL_PATH, USER_AGENT

class RateLimiter:
    def __init__(self, capacity=10, per_sec=0.5): self.cap, self.rate, self.b = capacity, per_sec, {}
    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now; tokens, last = self.b.get(key, (self.cap, now))
        tokens = min(self.cap, tokens + (now - last) * self.rate)
        if tokens < 1: self.b[key] = (tokens, now); return False
        self.b[key] = (tokens - 1, now); return True

def cached_json(key, ttl_s, fetch, base=None, now=None):
    base = base or (DATA / "cache"); base.mkdir(parents=True, exist_ok=True); f = base / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    now = time.time() if now is None else now
    if f.exists() and now - f.stat().st_mtime < ttl_s: return json.loads(f.read_text(encoding="utf-8"))
    v = fetch(); f.write_text(json.dumps(v), encoding="utf-8"); return v

def validate_analyze(r):
    e = []
    for k in ("acquirer", "target"):
        if not str(r.get(k, "")).strip(): e.append(f"{k} is required")
    for k in ("acquirer_price", "target_price"):
        if not (r.get(k) or 0) > 0: e.append(f"{k} must be > 0")
    rng = {"premium_pct": (0, 300), "pct_cash": (0, 100), "tax_rate": (0, 60), "cost_of_debt": (0, 30), "synergies_musd": (0, 1e6)}
    for k, (lo, hi) in rng.items():
        v = r.get(k)
        if v is not None and not lo <= v <= hi: e.append(f"{k} must be between {lo} and {hi}")
    if str(r.get("acquirer", "")).strip().lower() == str(r.get("target", "")).strip().lower() and r.get("acquirer"): e.append("acquirer and target must differ")
    return e

SUFFIX = re.compile(r"\b(inc|incorporated|corp|corporation|co|company|ltd|limited|llc|plc|holdings?|group|the)\b")
def normalize_company(name): return " ".join(SUFFIX.sub(" ", re.sub(r"[^a-z0-9 ]", " ", name.lower())).split())

def deep_health():
    import requests
    from .db import rows
    out = {"db": False, "ollama": False, "model_trained": MODEL_PATH.exists(), "sec_user_agent_ok": "@" in USER_AGENT and "example.com" not in USER_AGENT}
    try: rows("SELECT 1"); out["db"] = True
    except Exception: pass
    try: out["ollama"] = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).ok
    except Exception: pass
    out["ok"] = out["db"] and out["sec_user_agent_ok"]; return out
