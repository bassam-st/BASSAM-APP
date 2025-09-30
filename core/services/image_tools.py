from typing import List, Dict
from PIL import Image
import numpy as np, imagehash


def basic_image_tags(local_path: str) -> str:
    try:
        im = Image.open(local_path).convert("RGB")
        arr = np.array(im).reshape(-1, 3)
        mean = arr.mean(axis=0)
        w, h = im.size
        return f"image {w}x{h} avg_color rgb({int(mean[0])},{int(mean[1])},{int(mean[2])})"
    except Exception:
        return ""

def phash(local_path: str) -> str:
    try:
        return str(imagehash.phash(Image.open(local_path)))
    except Exception:
        return ""

def image_search_links(public_url: str, extra_query: str = "") -> List[Dict]:
    links = [
        {"name": "Google Lens", "url": f"https://lens.google.com/uploadbyurl?url={public_url}"},
        {"name": "Yandex Images", "url": f"https://yandex.com/images/search?rpt=imageview&url={public_url}"},
        {"name": "Bing Images", "url": f"https://www.bing.com/images/search?q=imgurl:{public_url}&view=detailv2&iss=1"},
    ]
    return links
