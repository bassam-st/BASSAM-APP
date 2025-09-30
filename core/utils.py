from typing import List
import os, json

def dedup_by_url(hits):
    seen, out = set(), []
    for h in hits:
        u = h.get("url");
        if not u or u in seen: continue
        seen.add(u); out.append(h)
    return out

def ensure_dirs(paths: List[str]):
    for p in paths:
        os.makedirs(p, exist_ok=True)
