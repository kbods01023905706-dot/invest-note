"""시세·지수·강세종목·수급 데이터를 모아 data/*.json 으로 저장한다.

GitHub Actions 러너에서 실행한다(지수·해외는 yfinance, 국내 강세종목·수급은 다음 금융).
각 항목은 실패해도 나머지가 계속 돌도록 개별 try 로 감싼다.
"""
import datetime as dt
import json
import os
import traceback

KST = dt.timezone(dt.timedelta(hours=9))
NOW = dt.datetime.now(KST)
ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")

US = [("S&P 500", "^GSPC"), ("나스닥", "^IXIC"), ("다우", "^DJI"), ("러셀 2000", "^RUT"),
      ("필라델피아 반도체", "^SOX"), ("VIX", "^VIX")]
KR = [("코스피", "^KS11"), ("코스닥", "^KQ11")]
MACRO = [("美 10년물 금리(%)", "^TNX"), ("달러인덱스", "DX-Y.NYB"), ("원/달러", "KRW=X"), ("달러/엔", "JPY=X"),
         ("WTI", "CL=F"), ("브렌트", "BZ=F"), ("금", "GC=F"), ("은", "SI=F"), ("구리", "HG=F"), ("비트코인", "BTC-USD")]
GLOBAL = [("닛케이225", "^N225"), ("항셍", "^HSI"), ("상하이종합", "000001.SS"), ("대만 가권", "^TWII"),
          ("인도 센섹스", "^BSESN"), ("STOXX 600", "^STOXX"), ("DAX", "^GDAXI"), ("FTSE 100", "^FTSE")]
US_STOCKS = [("엔비디아", "NVDA"), ("애플", "AAPL"), ("마이크로소프트", "MSFT"), ("아마존", "AMZN"), ("알파벳", "GOOGL"),
             ("메타", "META"), ("테슬라", "TSLA"), ("브로드컴", "AVGO"), ("AMD", "AMD"), ("마이크론", "MU"),
             ("TSMC ADR", "TSM"), ("팔란티어", "PLTR")]
INTRADAY = [("코스피", "^KS11"), ("코스닥", "^KQ11"), ("S&P 500", "^GSPC"), ("나스닥", "^IXIC")]


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def quotes(pairs):
    import yfinance as yf
    out = []
    for name, t in pairs:
        try:
            h = yf.Ticker(t).history(period="1mo", interval="1d", auto_adjust=False).dropna(subset=["Close"])
            c, p = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
            wk = float(h["Close"].iloc[-6]) if len(h) >= 6 else None
            out.append({
                "name": name, "ticker": t, "date": h.index[-1].strftime("%Y-%m-%d"),
                "close": round(c, 2), "chg": round(c - p, 2), "pct": round((c / p - 1) * 100, 2),
                "wk": round((c / wk - 1) * 100, 2) if wk else None,
                "spark": [round(float(x), 2) for x in h["Close"].tail(20)],
            })
        except Exception as e:
            out.append({"name": name, "ticker": t, "error": str(e)[:80]})
    return out


def intraday():
    """5분봉으로 장중 흐름과 전강후약/전약후강을 판정한다."""
    import yfinance as yf
    out = []
    for name, t in INTRADAY:
        try:
            h = yf.Ticker(t).history(period="5d", interval="5m").dropna(subset=["Close"])
            last_day = h.index[-1].date()
            d = h[h.index.date == last_day]
            closes = [float(x) for x in d["Close"]]
            o, c = float(d["Open"].iloc[0]), closes[-1]
            hi, lo = float(d["High"].max()), float(d["Low"].min())
            mid = closes[len(closes) // 2]
            first, second = mid - o, c - mid
            if first > 0 and second < 0:
                verdict = "전강후약"
            elif first < 0 and second > 0:
                verdict = "전약후강"
            elif first >= 0 and second >= 0:
                verdict = "강세 지속"
            else:
                verdict = "약세 지속"
            out.append({
                "name": name, "ticker": t, "date": str(last_day),
                "times": [x.strftime("%H:%M") for x in d.index],
                "closes": [round(x, 2) for x in closes],
                "open": round(o, 2), "high": round(hi, 2), "low": round(lo, 2), "close": round(c, 2),
                "pos": round((c - lo) / (hi - lo) * 100) if hi > lo else None,
                "verdict": verdict,
            })
        except Exception as e:
            out.append({"name": name, "ticker": t, "error": str(e)[:80]})
    return out


# ---------------------------------------------------------------------------
# 강세종목·수급: 다음 금융 공개 API
# (KRX 정보데이터시스템이 로그인 의무화된 뒤 pykrx·FinanceDataReader 의 KRX 수집이 막혔다)
# ---------------------------------------------------------------------------
DAUM = "https://finance.daum.net"
DAUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://finance.daum.net/",
    "Accept": "application/json, text/plain, */*",
}
INDEX_CODE = {"KOSPI": "KGG01P", "KOSDAQ": "QGG01P"}
STOCK_GROUPS = {"STOCK", "FOREIGN_STOCK"}  # ETF·ETN·리츠 등은 강세종목에서 뺀다


def daum(path, **params):
    import time
    import requests
    last = None
    for attempt in range(3):
        try:
            r = requests.get(DAUM + path, params=params, headers=DAUM_HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # 일시 오류는 두 번 더 시도
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def signed_rate(x):
    """다음 API 의 changeRate 는 부호가 없을 수 있어 change(RISE/FALL)로 부호를 붙인다(%)."""
    r = abs(float(x.get("changeRate") or 0)) * 100
    return -r if str(x.get("change", "")).upper() in ("FALL", "LOWER_LIMIT") else r


def market_list(mkt):
    """시장 전 종목(시가총액 순)의 현재가·등락률·시가총액."""
    out, page = [], 1
    while True:
        d = daum("/api/trend/market_capitalization", page=page, perPage=1000, fieldName="marketCap",
                 order="desc", market=mkt, pagination="true")
        out += d.get("data") or []
        if page >= int(d.get("totalPages") or 1):
            return out
        page += 1


def quote(symbol):
    return daum(f"/api/quotes/{symbol}", summary="false", changeStatistics="true")


def stock_row(x, q, mkt):
    return {
        "code": x["symbolCode"][1:], "name": x["name"], "market": mkt,
        "close": int(q.get("tradePrice") or x.get("tradePrice") or 0),
        "pct": round(signed_rate(q if q.get("change") else x), 2),
        "amount_eok": round(float(q.get("accTradePrice") or 0) / 1e8),
        "marcap_jo": round(float(q.get("marketCap") or x.get("marketCap") or 0) / 1e12, 2),
    }


def movers():
    MIN_CAP, MIN_AMT = 1e11, 5e9  # 시가총액 1,000억 원, 거래대금 50억 원
    universe = []
    for mkt in ("KOSPI", "KOSDAQ"):
        universe += [dict(x, _mkt=mkt) for x in market_list(mkt)]
    big = [x for x in universe if float(x.get("marketCap") or 0) >= MIN_CAP]

    cache = {}

    def q(x):
        s = x["symbolCode"]
        if s not in cache:
            try:
                cache[s] = quote(s)
            except Exception:
                cache[s] = {}
        return cache[s]

    def pick(cands, n):
        rows = []
        for x in cands:
            d = q(x)
            if d.get("securityGroup") not in STOCK_GROUPS:
                continue
            if float(d.get("accTradePrice") or 0) < MIN_AMT:
                continue
            rows.append(stock_row(x, d, x["_mkt"]))
            if len(rows) >= n:
                break
        return rows

    up = pick(sorted(big, key=signed_rate, reverse=True)[:60], 15)
    down = pick(sorted(big, key=signed_rate)[:45], 10)

    # 거래대금 상위: 시장별 거래대금 순 목록에서 주식만 골라 합친다
    amt = []
    for mkt in ("KOSPI", "KOSDAQ"):
        d = daum("/api/trend/market_capitalization", page=1, perPage=30, fieldName="accTradePrice",
                 order="desc", market=mkt, pagination="true")
        for x in d.get("data") or []:
            qd = q(dict(x, _mkt=mkt))
            if qd.get("securityGroup") in STOCK_GROUPS:
                amt.append(stock_row(x, qd, mkt))
    amt.sort(key=lambda r: r["amount_eok"], reverse=True)

    # 등락 종목 수: 지수 시세의 상승·하락·보합 집계(코스피+코스닥)
    breadth = {"up": 0, "down": 0, "flat": 0}
    for mkt, code in INDEX_CODE.items():
        st = (quote(code).get("changeStatistics") or {})
        breadth["up"] += int(st.get("riseCount") or 0)
        breadth["down"] += int(st.get("fallCount") or 0)
        breadth["flat"] += int(st.get("evenCount") or 0)

    return {
        "up": up, "down": down, "amount": amt[:10], "breadth": breadth,
        "filter": "주식만(ETF·ETN 제외), 시가총액 1,000억 원 이상·거래대금 50억 원 이상",
        "universe": len(universe),
    }


def flows():
    """시장별 투자자 순매수(억원). 다음은 개인·외국인·기관만 주므로 기타법인은 나머지(합계 0)로 계산."""
    out = {}
    for mkt in ("KOSPI", "KOSDAQ"):
        d = daum("/api/market_index/days", market=mkt, perPage=5)
        rows = d.get("data") or []
        if not rows:
            raise RuntimeError(f"{mkt} 수급 없음")
        x = rows[0]
        ind = float(x.get("individualStraightPurchasePrice") or 0)
        frn = float(x.get("foreignStraightPurchasePrice") or 0)
        ins = float(x.get("institutionStraightPurchasePrice") or 0)
        out[mkt] = {
            "date": str(x.get("date", ""))[:10],
            "개인": round(ind / 1e8), "외국인": round(frn / 1e8), "기관": round(ins / 1e8),
            "기타법인": round(-(ind + frn + ins) / 1e8),
        }
    return out


def run(name, fn):
    try:
        return fn()
    except Exception:
        traceback.print_exc()
        return {"error": f"{name} 수집 실패"}


def main():
    stamp = NOW.strftime("%Y-%m-%d %H:%M")
    save("market.json", {
        "updated": stamp,
        "kr": run("kr", lambda: quotes(KR)),
        "us": run("us", lambda: quotes(US)),
        "macro": run("macro", lambda: quotes(MACRO)),
        "global": run("global", lambda: quotes(GLOBAL)),
        "us_stocks": run("us_stocks", lambda: quotes(US_STOCKS)),
        "intraday": run("intraday", intraday),
        "source": "Yahoo Finance(yfinance) 일봉·5분봉",
    })
    save("movers.json", {"updated": stamp, **(run("movers", movers) or {}),
                         "flows": run("flows", flows), "source": "다음 금융(finance.daum.net) 공개 시세"})
    print("market updated", stamp)


if __name__ == "__main__":
    main()
