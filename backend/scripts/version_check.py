"""Prints which version of PrecedentFinder is installed. Run: python scripts\version_check.py"""
import pathlib
b = pathlib.Path(__file__).resolve().parents[1]; f = b.parent / "frontend"
checks = {
 "v1  extractor guards (VALUE_WINDOW)": ("app/extractor.py", "VALUE_WINDOW"),
 "v2  date/range/outlier guards": ("app/extractor.py", "premium_outlier_gt100"),
 "v2  deal analyzer backend": ("app/analyze.py", "def run("),
 "v3  features pack (risk flags, football)": ("app/features.py", "def risk_flags"),
 "v4  features pack 2 (compare, watchlist)": ("app/features.py", "def watch_add"),
}
for name, (p, s) in checks.items():
    t = (b / p).read_text(encoding="utf-8") if (b / p).exists() else ""; print(("OK      " if s in t else "MISSING ") + name)
for name, p in {"v3  landing page": "components/Landing.tsx", "v3  insights": "components/Insights.tsx", "v4  tools": "components/Tools.tsx"}.items():
    print(("OK      " if (f / p).exists() else "MISSING ") + name)
print("\nLatest = everything OK and 'pytest tests' shows 39 passed.")
