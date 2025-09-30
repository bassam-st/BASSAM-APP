# core/providers.py — quick price lookups via search URLs
from typing import List, Dict
from urllib.parse import quote_plus

SITES = {
    "Amazon": "https://www.amazon.com/s?k={q}",
    "Noon": "https://www.noon.com/uae-en/search?q={q}",
    "AliExpress": "https://www.aliexpress.com/wholesale?SearchText={q}",
    "Alibaba": "https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&SearchText={q}",
    "Amazon.sa": "https://www.amazon.sa/s?k={q}",
    "Amazon.ae": "https://www.amazon.ae/s?k={q}",
}

def price_lookup_grouped(query: str) -> List[Dict]:
    q = quote_plus(query)
    out = []
    for name, tpl in SITES.items():
        out.append({"site": name, "url": tpl.format(q=q)})
    return out
