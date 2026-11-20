"""DART 공시를 가져와 실적발표 종목 데이터와 종목별 실적 리포트 페이지를 만든다.

- 최근 며칠간의 분기·반기·사업보고서와 (잠정)실적 공정공시를 모은다.
- 정기보고서는 주요계정(매출·영업이익·순이익)을 조회해 전분기/전년동기와 비교한다.
- 영업이익 전분기 대비 +50% 이상, 전년동기 대비 +50% 이상, 또는 흑자전환이면 '실적 급증'으로 표시한다.
- 급증 종목과 대형 종목은 reports/ 아래에 리포트 페이지를 자동 생성한다.
환경변수 DART_API_KEY 가 필요하다(GitHub Secrets).
"""
import datetime as dt
import html
import io
import json
import os
import time
import zipfile
import xml.etree.ElementTree as ET

import requests

KEY = os.environ.get("DART_API_KEY", "").strip()
API = "https://opendart.fss.or.kr/api"
KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST)
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")
LOOKBACK_DAYS = int(os.environ.get("DART_LOOKBACK_DAYS", "4"))
MAX_REPORT_CALLS = int(os.environ.get("DART_MAX_CALLS", "120"))
KEEP_DAYS = 60
MIN_OP = int(os.environ.get("DART_MIN_OP", "1000000000"))  # 급증 표시 최소 영업이익(10억 원)

REPRT = {"03": "11013", "06": "11012", "09": "11014", "12": "11011"}
REPRT_NAME = {"11013": "1분기", "11012": "반기(2분기)", "11014": "3분기", "11011": "연간(사업보고서)"}
PREV_Q = {"11014": "11012", "11012": "11013"}  # 3개월 값 비교가 가능한 직전 분기


def get(path, **params):
    params["crtfc_key"] = KEY
    for i in range(3):
        try:
            r = requests.get(f"{API}/{path}", params=params, timeout=30)
            if path.endswith(".json"):
                return r.json()
            return r.content
        except Exception:
            time.sleep(2 * (i + 1))
    return {}


def load(name, default):
    p = os.path.join(DATA, name)
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def to_num(s):
    if s in (None, "", "-"):
        return None
    try:
        return int(str(s).replace(",", "").strip())
    except ValueError:
        return None


def disclosures(kind):
    """kind: A(정기공시) / I(거래소공시) / B(주요사항보고)."""
    out, page = [], 1
    bgn = (NOW - dt.timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    end = NOW.strftime("%Y%m%d")
    while True:
        d = get("list.json", bgn_de=bgn, end_de=end, pblntf_ty=kind, page_count=100, page_no=page)
        if not d or d.get("status") != "000":
            break
        out += [x for x in d.get("list", []) if x.get("corp_cls") in ("Y", "K") and x.get("stock_code")]
        if page >= int(d.get("total_page", 1)) or page >= 40:
            break
        page += 1
    return out


def accounts(corp_code, year, reprt):
    d = get("fnlttSinglAcnt.json", corp_code=corp_code, bsns_year=year, reprt_code=reprt)
    if not d or d.get("status") != "000":
        return None
    rows = d.get("list", [])
    fs = "CFS" if any(r.get("fs_div") == "CFS" for r in rows) else "OFS"
    res = {"fs": fs}
    for r in rows:
        if r.get("fs_div") != fs or r.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = r.get("account_nm", "")
        key = None
        if nm.startswith("매출액") or nm in ("수익(매출액)", "영업수익"):
            key = "sales"
        elif nm.startswith("영업이익"):
            key = "op"
        elif nm.startswith("당기순이익"):
            key = "net"
        if key and key not in res:
            res[key] = {
                "cur": to_num(r.get("thstrm_amount")),
                "cur_cum": to_num(r.get("thstrm_add_amount")),
                "yoy": to_num(r.get("frmtrm_amount")),
            }
    return res


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return round((a / b - 1) * 100, 1) if b > 0 else None


def flags_for(op_cur, op_prev, op_yoy):
    f = []
    if op_cur is not None and op_prev is not None:
        if op_prev <= 0 < op_cur:
            f.append("흑자전환(QoQ)")
        elif op_prev > 0 and op_cur >= op_prev * 1.5:
            f.append("영업이익 +50%↑(QoQ)")
        elif op_prev > 0 > op_cur:
            f.append("적자전환(QoQ)")
    if op_cur is not None and op_yoy is not None:
        if op_yoy <= 0 < op_cur:
            f.append("흑자전환(YoY)")
        elif op_yoy > 0 and op_cur >= op_yoy * 1.5:
            f.append("영업이익 +50%↑(YoY)")
        elif op_yoy > 0 > op_cur:
            f.append("적자전환(YoY)")
    return f


def funding_count(corp_code):
    """최근 1년 전환사채·신주인수권부사채·교환사채·유상증자 결정 공시 건수."""
    bgn = (NOW - dt.timedelta(days=365)).strftime("%Y%m%d")
    d = get("list.json", corp_code=corp_code, bgn_de=bgn, end_de=NOW.strftime("%Y%m%d"), pblntf_ty="B", page_count=100)
    n = 0
    for x in (d or {}).get("list", []) or []:
        nm = x.get("report_nm", "")
        if "정정" in nm:
            continue
        if any(k in nm for k in ("전환사채권발행결정", "신주인수권부사채권발행결정", "교환사채권발행결정", "유상증자결정")):
            n += 1
    return n


def won(v):
    if v is None:
        return "—"
    eok = v / 1e8
    if abs(eok) >= 10000:
        return f"{eok/10000:,.2f}조"
    return f"{eok:,.0f}억"


def change_html(a, b):
    """이번 값 a 와 비교 값 b 의 변화를 표시한다(부호가 바뀌면 전환으로 표기)."""
    if a is None or b is None:
        return '<span class="fl">—</span>'
    if b <= 0 < a:
        return '<span class="up">흑자전환</span>'
    if a < 0 <= b:
        return '<span class="dn">적자전환</span>' if b > 0 else '<span class="dn">적자</span>'
    if a <= 0 and b < 0:
        return '<span class="dn">적자지속</span>'
    return pct_html(pct(a, b))


def pct_html(p):
    if p is None:
        return '<span class="fl">—</span>'
    cls = "up" if p > 0 else ("dn" if p < 0 else "fl")
    arrow = "▲" if p > 0 else ("▼" if p < 0 else "")
    return f'<span class="{cls}">{arrow}{p:+.1f}%</span>'


def write_report(item):
    os.makedirs(REPORTS, exist_ok=True)
    fn = f"{item['stock_code']}_{item['rcept_no']}.html"
    rows = ""
    for key, label in (("sales", "매출액"), ("op", "영업이익"), ("net", "순이익")):
        a = item["acc"].get(key, {})
        cur, prev, yoy = a.get("cur"), a.get("prev"), a.get("yoy")
        rows += (f"<tr><th>{label}</th><td>{won(cur)}</td><td>{won(prev)}</td><td>{change_html(cur, prev)}</td>"
                 f"<td>{won(yoy)}</td><td>{change_html(cur, yoy)}</td></tr>")
    s = item["acc"].get("sales", {}).get("cur")
    o = item["acc"].get("op", {}).get("cur")
    margin = f"{o / s * 100:.1f}%" if s and o is not None else "—"
    fund = item.get("funding")
    fund_txt = "—" if fund is None else f"{fund}건"
    checks = []
    if fund is not None and fund >= 2:
        checks.append("최근 1년 CB·BW·EB·유상증자 결정이 2건 이상 — 희석 가능성 점검")
    if "적자전환(QoQ)" in item["flags"] or "적자전환(YoY)" in item["flags"]:
        checks.append("영업이익 적자전환 — 일회성 비용 여부를 사업보고서 주석에서 확인")
    if not checks:
        checks.append("자동 점검 항목에서 특이사항 없음 — 영업현금흐름·재고·매출채권 증감은 원문에서 확인")
    tags = "".join(f'<span class="chip">{html.escape(f)}</span>' for f in item["flags"]) or '<span class="chip muted">특이 신호 없음</span>'
    body = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(item['corp_name'])} 실적 리포트</title>
<link rel="stylesheet" href="../style.css"></head><body class="report">
<header class="topbar"><div class="wrap"><a class="brand" href="../index.html#earnings">← 이중재의 투자노트</a></div></header>
<main class="wrap">
<p class="eyebrow">자동 생성 실적 리포트 · {html.escape(item['period'])}</p>
<h1>{html.escape(item['corp_name'])} <small>{item['stock_code']} · {'코스피' if item['corp_cls']=='Y' else '코스닥'}</small></h1>
<div class="chips">{tags}</div>
<section class="card"><h2>손익 요약 ({'연결' if item['acc'].get('fs')=='CFS' else '별도'}, 3개월 기준)</h2>
<div class="scroll"><table class="tbl"><thead><tr><th>항목</th><th>이번 분기</th><th>직전 분기</th><th>QoQ</th><th>전년 동기</th><th>YoY</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="note">영업이익률 {margin}. 직전 분기 값은 3분기·반기보고서에서만 비교합니다(1분기·연간은 전년 동기 비교).</p></section>
<section class="card"><h2>자동 점검</h2><ul>{''.join(f'<li>{html.escape(c)}</li>' for c in checks)}</ul>
<p class="note">최근 1년 자금조달 결정 공시: {fund_txt}</p></section>
<section class="card"><h2>원문</h2><p><a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item['rcept_no']}" target="_blank" rel="noopener">DART에서 {html.escape(item['report_nm'])} 열기</a> · 접수 {item['rcept_dt']}</p></section>
<p class="disc">OpenDART 주요계정 API로 자동 생성한 참고 자료이며 매매 권유가 아닙니다. 숫자는 원문 공시와 반드시 대조하세요.</p>
</main></body></html>"""
    with open(os.path.join(REPORTS, fn), "w", encoding="utf-8") as f:
        f.write(body)
    return f"reports/{fn}"


def corp_names():
    """상장사 corp_code → 기본정보 캐시(주 1회 갱신)."""
    cache = load("corp_codes.json", {})
    if cache.get("updated", "") >= (NOW - dt.timedelta(days=7)).strftime("%Y-%m-%d"):
        return cache
    raw = get("corpCode.xml")
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        root = ET.fromstring(z.read(z.namelist()[0]))
        m = {}
        for e in root.iter("list"):
            sc = (e.findtext("stock_code") or "").strip()
            if sc:
                m[e.findtext("corp_code")] = {"name": e.findtext("corp_name"), "stock": sc}
        cache = {"updated": NOW.strftime("%Y-%m-%d"), "count": len(m)}
        save("corp_codes.json", cache)
    except Exception:
        pass
    return cache


def finalize(feed, reports, calls):
    cutoff = (NOW - dt.timedelta(days=KEEP_DAYS)).strftime("%Y%m%d")
    feed_list = sorted([v for v in feed.values() if v["rcept_dt"] >= cutoff], key=lambda v: v["rcept_no"], reverse=True)
    reps = sorted([r for r in reports if r["rcept_dt"] >= cutoff], key=lambda r: r["rcept_no"], reverse=True)
    save("earnings.json", {
        "updated": NOW.strftime("%Y-%m-%d %H:%M"),
        "status": "정상",
        "criteria": "영업이익(3개월) 10억 원 이상이면서 전분기 대비 +50% 이상, 전년 동기 대비 +50% 이상, 또는 흑자전환",
        "feed": feed_list[:400],
        "reports": reps[:600],
    })
    print(f"feed {len(feed_list)} / reports {len(reps)} / api calls {calls}")


def main():
    global LOOKBACK_DAYS, MAX_REPORT_CALLS
    old = load("earnings.json", {"feed": [], "reports": []})
    if not old.get("reports"):  # 첫 실행: 최근 2주를 넉넉히 수집
        LOOKBACK_DAYS, MAX_REPORT_CALLS = max(LOOKBACK_DAYS, 14), max(MAX_REPORT_CALLS, 400)
    if not KEY:
        old["status"] = "DART_API_KEY 미설정 — GitHub Secrets에 등록하세요"
        save("earnings.json", old)
        return
    corp_names()
    regular = [x for x in disclosures("A") if any(k in x["report_nm"] for k in ("분기보고서", "반기보고서", "사업보고서"))]
    prelim = [x for x in disclosures("I") if "잠정" in x["report_nm"] and "실적" in x["report_nm"]]

    feed = {x["rcept_no"]: x for x in old.get("feed", [])}
    for x in regular + prelim:
        feed[x["rcept_no"]] = {
            "rcept_no": x["rcept_no"], "rcept_dt": x["rcept_dt"], "corp_name": x["corp_name"],
            "stock_code": x["stock_code"], "corp_cls": x["corp_cls"],
            "report_nm": " ".join(x["report_nm"].split()),
            "kind": "잠정실적" if x in prelim else "정기보고서",
        }

    done = {r["rcept_no"] for r in old.get("reports", [])}
    reports = list(old.get("reports", []))
    calls = 0
    for x in regular:
        if x["rcept_no"] in done or calls >= MAX_REPORT_CALLS or "정정" in x["report_nm"]:
            continue
        nm = x["report_nm"]
        try:
            ym = nm.split("(")[1].split(")")[0]  # 2026.09
            year, mon = ym.split(".")
        except Exception:
            continue
        reprt = REPRT.get(mon)
        if not reprt:
            continue
        acc = accounts(x["corp_code"], year, reprt)
        calls += 1
        if not acc or "op" not in acc:
            continue
        if reprt in PREV_Q:
            prev = accounts(x["corp_code"], year, PREV_Q[reprt])
            calls += 1
            for k in ("sales", "op", "net"):
                if k in acc:
                    acc[k]["prev"] = (prev or {}).get(k, {}).get("cur")
        op = acc["op"]
        flags = flags_for(op.get("cur"), op.get("prev"), op.get("yoy"))
        # 영업이익 10억 원 미만은 기저효과 잡음이 커서 급증 표시에서 제외
        surge = (op.get("cur") or 0) >= MIN_OP and any(("+50%" in f) or ("흑자전환" in f) for f in flags)
        item = {
            "rcept_no": x["rcept_no"], "rcept_dt": x["rcept_dt"], "corp_name": x["corp_name"],
            "stock_code": x["stock_code"], "corp_cls": x["corp_cls"], "report_nm": " ".join(nm.split()),
            "period": f"{year}년 {REPRT_NAME[reprt]}", "acc": acc, "flags": flags, "surge": surge,
        }
        if surge:
            item["funding"] = funding_count(x["corp_code"])
            calls += 1
            item["file"] = write_report(item)
        reports.append({k: item.get(k) for k in ("rcept_no", "rcept_dt", "corp_name", "stock_code", "corp_cls",
                                                    "report_nm", "period", "flags", "surge", "file", "funding")} |
                       {"op": op.get("cur"), "op_prev": op.get("prev"), "op_yoy": op.get("yoy"),
                        "sales": acc.get("sales", {}).get("cur")})
        if len(reports) % 25 == 0:
            finalize(feed, reports, calls)

    finalize(feed, reports, calls)

if __name__ == "__main__":
    main()
