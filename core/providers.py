from urllib.parse import quote_plus

SITES = {
    "Amazon": "https://www.amazon.com/s?k={q}",
    "Noon": "https://www.noon.com/uae-en/search?q={q}",
    "AliExpress": "https://www.aliexpress.com/wholesale?SearchText={q}",
    "Alibaba": "https://www.alibaba.com/trade/search?fsb=y&IndexArea=product_en&SearchText={q}",
    "Amazon.sa": "https://www.amazon.sa/s?k={q}",
    "Amazon.ae": "https://www.amazon.ae/s?k={q}",
}

SOCIAL = {
    "Google": "https://www.google.com/search?q={q}",
    "Facebook": "https://www.facebook.com/search/top?q={q}",
    "Twitter": "https://x.com/search?q={q}",
    "Instagram": "https://www.instagram.com/explore/tags/{q}",
    "LinkedIn": "https://www.linkedin.com/search/results/all/?keywords={q}",
    "TikTok": "https://www.tiktok.com/search?q={q}",
    "YouTube": "https://www.youtube.com/results?search_query={q}",
}

def price_lookup_grouped(query: str):
    q = quote_plus(query); return [{"site": n, "url": u.format(q=q)} for n, u in SITES.items()]

def profile_links(name: str):
    q = quote_plus(name)
    links = [{"site": n, "url": u.format(q=q)} for n, u in SOCIAL.items()]
    # common username patterns
    base = name.strip().replace(" ", "")
    for site, fmt in [
        ("Instagram (username)", f"https://www.instagram.com/{base}"),
        ("Twitter (username)", f"https://x.com/{base}"),
        ("GitHub (username)", f"https://github.com/{base}")
    ]:
        links.append({"site": site, "url": fmt})
    return links
