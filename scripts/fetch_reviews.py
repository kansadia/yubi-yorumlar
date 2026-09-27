#!/usr/bin/env python3
"""Yubi Design - Trendyol yorumlarini cekip GitHub Pages icin JSON uretir.

Cikti:
  docs/r/<SKU>.json   -> urun bazli yorumlar (ikas SKU = Trendyol productCode)
  docs/index.json     -> ozet (hangi SKU'da kac yorum var)
  data/map.json       -> Trendyol contentId -> {slug, code} (tekrar tekrar urun sayfasi cekmemek icin)
"""
import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

MERCHANT_ID = 576987
MIN_RATE = 3
MAX_PAGES_SEARCH = 40
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "docs", "r")
IMG_DIR = os.path.join(ROOT, "docs", "img")
MAP_FILE = os.path.join(ROOT, "data", "map.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Cookie": "storefrontId=1; countryCode=TR; language=tr; platform=web",
    "Origin": "https://www.trendyol.com",
    "Referer": "https://www.trendyol.com/",
}
REVIEW_URL = ("https://apigw.trendyol.com/discovery-storefront-trproductgw-service/api/review-read/"
              "product-reviews/detailed?channelId=1&merchantId={m}&contentId={cid}&page={p}"
              "&pageSize=50&order=DESC&orderBy=Score")


def get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def get(url, retries=4):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404,):
                return None
            err = e
            if e.code == 429:
                time.sleep(30 * (i + 1))
                continue
        except Exception as e:  # noqa
            err = e
        time.sleep(2 + i * 3)
    raise RuntimeError(f"GET basarisiz: {url.split('?')[0]} -> {err}")


TR_UP = {"i": "İ", "ı": "I"}


def initials(name):
    parts = []
    for w in name.split():
        w = re.sub(r"[^A-Za-zÇĞİÖŞÜçğıöşü]", "", w)
        if w:
            c = w[0]
            parts.append(TR_UP.get(c, c.upper()) + "**")
    return " ".join(parts) if parts else "*** ***"


def list_products():
    found = {}
    empty = 0
    for pi in range(1, MAX_PAGES_SEARCH + 1):
        html = get(f"https://www.trendyol.com/sr?mid={MERCHANT_ID}&os=1&pi={pi}") or ""
        before = len(found)
        for slug, cid in re.findall(r"/yubi-design/([a-z0-9-]+)-p-(\d+)", html):
            found.setdefault(cid, slug)
        if len(found) == before:
            empty += 1
            if empty >= 2:
                break
        else:
            empty = 0
        time.sleep(0.5)
    return found


def product_code(cid, slug):
    html = get(f"https://www.trendyol.com/yubi-design/{slug}-p-{cid}") or ""
    m = re.search(r'"id":%s,"name":"[^"]*","productCode":"([^"]+)"' % cid, html) \
        or re.search(r'"productCode":"([^"]+)"', html)
    return m.group(1) if m else None


def fetch_reviews(cid):
    reviews, page, summary = [], 0, {}
    while True:
        txt = get(REVIEW_URL.format(m=MERCHANT_ID, cid=cid, p=page))
        if not txt:
            break
        res = (json.loads(txt).get("result") or {})
        summary = res.get("summary") or summary
        reviews += res.get("reviews") or []
        page += 1
        if page >= (summary.get("totalPages") or 1) or page > 20:
            break
        time.sleep(0.3)
    return summary, reviews


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    pmap = json.load(open(MAP_FILE)) if os.path.exists(MAP_FILE) else {}

    products = list_products()
    print(f"Trendyol'da {len(products)} urun bulundu")
    if len(products) < 50:
        print("HATA: Urun listesi beklenenden az - Trendyol erisimi engellenmis olabilir.")
        sys.exit(1)

    for cid, slug in products.items():
        pmap.setdefault(cid, {"code": None})["slug"] = slug

    by_sku = {}
    failed = 0
    for cid, slug in products.items():
        try:
            summary, reviews = fetch_reviews(cid)
        except Exception as e:  # noqa
            print(f"Yorum cekilemedi: {cid} ({e})")
            failed += 1
            continue
        time.sleep(0.4)
        if not summary.get("totalRatingCount"):
            continue
        good = [r for r in reviews
                if (r.get("rate") or 0) >= MIN_RATE and (r.get("comment") or "").strip()
                and "trendyol" not in (r.get("comment") or "").lower()]
        code = pmap[cid].get("code")
        if not code:
            try:
                code = product_code(cid, slug)
                pmap[cid]["code"] = code
            except Exception as e:  # noqa
                print(f"Urun kodu alinamadi: {cid} ({e})")
            time.sleep(1.5)
        if not code:
            continue
        b = by_sku.setdefault(code, {"sum": 0.0, "ratings": 0, "reviews": []})
        n = summary.get("totalRatingCount") or 0
        b["sum"] += (summary.get("averageRating") or 0) * n
        b["ratings"] += n
        for r in good:
            text = r["comment"].strip()
            imgs = []
            media = [m for m in (r.get("mediaFiles") or []) if m.get("mediaType") == "IMAGE" and m.get("url")]
            for k, m in enumerate(media[:4], 1):
                fn = f"{re.sub(r'[^A-Za-z0-9_-]', '_', code)}_{r.get('id')}_{k}.jpg"
                path = os.path.join(IMG_DIR, fn)
                if not os.path.exists(path):
                    try:
                        data = get_bytes(m["url"])
                        with open(path, "wb") as fh:
                            fh.write(data)
                    except Exception as e:  # noqa
                        print(f"Gorsel indirilemedi: {fn} ({e})")
                        continue
                imgs.append(fn)
            b["reviews"].append({
                "n": initials(r.get("userFullName") or ""),
                "r": r.get("rate"),
                "t": text,
                "d": r.get("createdAt"),
                "i": imgs,
            })

    print(f"Yorum cekme hatasi: {failed}/{len(products)}")
    if failed > len(products) * 0.2 or not by_sku:
        print("HATA: Cok fazla hata - mevcut veriler korunuyor, hicbir sey yazilmadi.")
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    index = {}
    for f in os.listdir(OUT_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(OUT_DIR, f))
    for sku, b in by_sku.items():
        b["reviews"].sort(key=lambda x: (len(x["i"]) > 0, x["r"], x["d"] or 0), reverse=True)
        avg = round(b["sum"] / b["ratings"], 1) if b["ratings"] else None
        out = {"sku": sku, "avg": avg, "ratings": b["ratings"], "updated": now, "reviews": b["reviews"]}
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", sku)
        with open(os.path.join(OUT_DIR, f"{safe}.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
        index[sku] = {"avg": avg, "ratings": b["ratings"], "comments": len(b["reviews"])}

    with open(os.path.join(ROOT, "docs", "index.json"), "w", encoding="utf-8") as fh:
        json.dump({"updated": now, "products": index}, fh, ensure_ascii=False, indent=1)
    with open(MAP_FILE, "w", encoding="utf-8") as fh:
        json.dump(pmap, fh, ensure_ascii=False, indent=0, sort_keys=True)

    total = sum(v["comments"] for v in index.values())
    print(f"{len(index)} urun icin {total} yorum yazildi ({MIN_RATE}+ yildiz, metinli)")


if __name__ == "__main__":
    main()
