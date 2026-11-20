"""시세·지수·강세종목·수급 데이터를 모아 data/*.json 으로 저장한다.

GitHub Actions 러너에서 실행한다(yfinance, FinanceDataReader, pykrx 사용).
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


def movers():
    import FinanceDataReader as fdr
    df = fdr.StockListing("KRX")
    df = df[df["Market"].isin(["KOSPI", "KOSDAQ"])].copy()
    df["Amount"] = df["Amount"].fillna(0)
    liquid = df[(df["Marcap"] >= 1e11) & (df["Amount"] >= 5e9)]

    def rows(sub, n):
        return [{
            "code": r.Code, "name": r.Name, "market": r.Market, "close": int(r.Close),
            "pct": round(float(r.ChagesRatio), 2), "amount_eok": round(float(r.Amount) / 1e8),
            "marcap_jo": round(float(r.Marcap) / 1e12, 2),
        } for r in sub.head(n).itertuples()]

    return {
        "up": rows(liquid.sort_values("ChagesRatio", ascending=False), 15),
        "down": rows(liquid.sort_values("ChagesRatio"), 10),
        "amount": rows(df.sort_values("Amount", ascending=False), 10),
        "breadth": {
            "up": int((df["ChagesRatio"] > 0).sum()), "down": int((df["ChagesRatio"] < 0).sum()),
            "flat": int((df["ChagesRatio"] == 0).sum()),
        },
        "filter": "시가총액 1,000억 원 이상·거래대금 50억 원 이상",
    }


def flows():
    from pykrx import stock
    end = NOW.strftime("%Y%m%d")
    start = (NOW - dt.timedelta(days=10)).strftime("%Y%m%d")
    out = {}
    for mkt in ("KOSPI", "KOSDAQ"):
        df = stock.get_market_trading_value_by_date(start, end, mkt)
        last = df.iloc[-1]
        out[mkt] = {
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "개인": round(float(last.get("개인", 0)) / 1e8),
            "외국인": round(float(last.get("외국인합계", 0)) / 1e8),
            "기관": round(float(last.get("기관합계", 0)) / 1e8),
            "기타법인": round(float(last.get("기타법인", 0)) / 1e8),
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
                         "flows": run("flows", flows), "source": "KRX(FinanceDataReader·pykrx)"})
    print("market updated", stamp)


if __name__ == "__main__":
    main()
