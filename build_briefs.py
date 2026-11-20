"""briefs/ 폴더의 PDF 목록을 data/briefs.json 으로 정리한다.
파일명 규칙: 아침통합브리핑_YYYYMMDD.pdf (다른 이름도 목록에는 표시)."""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
items = []
paths = [("", fn) for fn in os.listdir(ROOT)]
if os.path.isdir(os.path.join(ROOT, "briefs")):
    paths += [("briefs/", fn) for fn in os.listdir(os.path.join(ROOT, "briefs"))]
for prefix, fn in paths:
    if not fn.lower().endswith(".pdf"):
        continue
    m = re.search(r"(\d{4})(\d{2})(\d{2})", fn)
    date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""
    items.append({"file": f"{prefix}{fn}", "date": date, "title": os.path.splitext(fn)[0].replace("_", " ")})
items.sort(key=lambda x: (x["date"], x["file"]), reverse=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "briefs.json"), "w", encoding="utf-8") as f:
    json.dump({"items": items}, f, ensure_ascii=False, indent=1)
print(len(items), "briefs")
