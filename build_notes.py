"""notes/ 폴더의 AI 시황노트(마크다운)를 data/notes.json 으로 정리한다.

파일 이름: YYYY-MM-DD-종류.md (예: 2026-11-28-morning.md, 2026-11-28-earnings-삼성전자.md)
첫 줄 '# 제목' 은 제목으로 쓰고, 나머지는 본문으로 그대로 넘긴다(화면에서 간단한 마크다운으로 그린다).
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(ROOT, "notes")
KIND = {"morning": "아침 시황", "close": "장마감", "earnings": "실적 해설", "research": "리서치 요약", "weekly": "주간"}

items = []
if os.path.isdir(NOTES):
    for fn in os.listdir(NOTES):
        if not fn.endswith(".md") or fn.lower() == "readme.md":
            continue
        with open(os.path.join(NOTES, fn), encoding="utf-8") as f:
            text = f.read().strip()
        m = re.match(r"(\d{4}-\d{2}-\d{2})-([a-z]+)", fn)
        date, kind = (m.group(1), m.group(2)) if m else ("", "")
        lines = text.splitlines()
        title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else os.path.splitext(fn)[0]
        body = "\n".join(lines[1:]).strip() if lines and lines[0].startswith("#") else text
        items.append({"file": f"notes/{fn}", "date": date, "kind": KIND.get(kind, kind or "노트"),
                      "title": title, "body": body})
items.sort(key=lambda x: (x["date"], x["file"]), reverse=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "notes.json"), "w", encoding="utf-8") as f:
    json.dump({"items": items[:120]}, f, ensure_ascii=False, indent=1)
print("notes", len(items))
