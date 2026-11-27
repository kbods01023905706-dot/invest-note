"""증권사 기업 리포트를 모아 목표주가 변동(상향·하향)을 계산한다.

출처: 한경 컨센서스(consensus.hankyung.com) 기업 리포트 목록 — 작성일, 제목, 적정가격(목표주가),
투자의견, 작성자, 증권사, PDF 링크, 요약 문장.
같은 종목·같은 증권사의 직전 리포트 목표주가와 비교해 상향/하향/유지/신규를 붙인다.
처음 실행이면 최근 90일을 받아 비교 기준을 만든다.
"""
import datetime as dt
import html
import json
import os
import re
import time

import requests

KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST)
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
DB = os.path.join(DATA, "research_db.json")
OUT = os.path.join(DATA, "research.json")

BASE = "https://consensus.hankyung.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": BASE + "/analysis/list",
}
PER_PAGE = 80
KEEP_DAYS = 400       # 비교 기준으로 보관하는 기간
BACKFILL_DAYS = 90    # 처음 실행 때 받는 기간
RECENT_DAYS = 7       # 화면에 보여 주는 기간(달력 기준)


def strip(s):
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return " ".join(html.unescape(s).split())


def parse(page_html):
    if "<tbody" not in page_html:
        return []
    body = page_html.split("<tbody", 1)[1].split("</tbody>", 1)[0]
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 6:
            continue
        m = re.search(r'report_idx=(\d+)"[^>]*>(.*?)</a>', tds[1], re.S)
        if not m:
            continue
        idx, title = m.group(1), strip(m.group(2))
        cm = re.search(r"\(([0-9A-Z]{6})\)", title)
        points = [strip(x) for x in re.findall(r"<li>(.*?)</li>", tds[1], re.S)]
        tp = re.sub(r"[^\d]", "", strip(tds[2]))
        out.append({
            "idx": int(idx),
            "date": strip(tds[0]),
            "title": title,
            "name": title.split("(")[0].strip() if cm else "",
            "code": cm.group(1) if cm else "",
            "target": int(tp) if tp else None,
            "opinion": strip(tds[3]),
            "author": strip(tds[4]),
            "broker": strip(tds[5]),
            "points": [p for p in points if p][:3],
            "pdf": f"{BASE}/analysis/downpdf?report_idx={idx}",
        })
    return out


def fetch(sdate, edate):
    items, page = [], 1
    while page <= 80:
        params = {"sdate": sdate, "edate": edate, "now_page": page, "search_value": "",
                  "report_type": "CO", "pagenum": PER_PAGE, "search_text": "", "business_code": ""}
        for attempt in range(3):
            try:
                r = requests.get(BASE + "/analysis/list", params=params, headers=HEADERS, timeout=30)
                r.raise_for_status()
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        r.encoding = r.apparent_encoding or "utf-8"
        rows = parse(r.text)
        items += rows
        if len(rows) < PER_PAGE:
            break
        page += 1
        time.sleep(0.5)
    return items


def load_db():
    try:
        with open(DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items": {}}


def main():
    db = load_db()
    first = not db.get("items")
    start = NOW - dt.timedelta(days=BACKFILL_DAYS if first else 5)
    new = fetch(start.strftime("%Y-%m-%d"), NOW.strftime("%Y-%m-%d"))
    for x in new:
        db["items"][str(x["idx"])] = x

    cutoff = (NOW - dt.timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    db["items"] = {k: v for k, v in db["items"].items() if v["date"] >= cutoff}

    # 같은 종목·같은 증권사의 직전 목표주가와 비교
    allx = sorted(db["items"].values(), key=lambda x: (x["date"], x["idx"]))
    last = {}
    for x in allx:
        key = (x["code"], x["broker"])
        prev = last.get(key)
        x.pop("prev", None), x.pop("chg", None), x.pop("move", None)
        if x["target"] is None:
            x["move"] = "없음"
        elif prev is None:
            x["move"] = "신규"
        else:
            x["prev"], x["prev_date"] = prev["target"], prev["date"]
            x["chg"] = round((x["target"] / prev["target"] - 1) * 100, 1) if prev["target"] else None
            x["move"] = "상향" if x["target"] > prev["target"] else "하향" if x["target"] < prev["target"] else "유지"
        if x["code"] and x["target"] is not None:
            last[key] = x

    recent_cut = (NOW - dt.timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
    recent = [x for x in reversed(allx) if x["date"] >= recent_cut]
    latest = recent[0]["date"] if recent else None
    today = [x for x in recent if x["date"] == latest]

    os.makedirs(DATA, exist_ok=True)
    with open(DB, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "updated": NOW.strftime("%Y-%m-%d %H:%M"),
            "latest": latest,
            "summary": {"total": len(today), "up": sum(x["move"] == "상향" for x in today),
                        "down": sum(x["move"] == "하향" for x in today)},
            "items": recent[:400],
            "source": "한경 컨센서스 기업 리포트",
            "note": "변동은 같은 종목·같은 증권사의 직전 리포트 목표주가와 비교",
        }, f, ensure_ascii=False, indent=1)
    print("research", len(new), "fetched,", len(db["items"]), "kept,", len(recent), "recent")


if __name__ == "__main__":
    main()
