#!/usr/bin/env python3
"""Build catalog + JSONL + inverted search index from the JSON corpus.

Does not copy binaries. Source files stay in exams/, schemes-of-work/, etc.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = [
    "exams",
    "lesson-notes",
    "lesson-plans",
    "revision",
    "schemes-of-work",
    "learning-docs",
]
SKIP_NAMES = {"manifest.json", "catalog.json", "_convert_stats.json", "structure.json"}

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "in", "out", "on", "off", "over", "under", "again", "further", "once",
    "here", "there", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "don", "should", "now",
    "of", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "this", "that", "these", "those", "it", "its",
    "as", "we", "you", "he", "she", "they", "them", "his", "her", "our",
    "your", "i", "me", "my",
}


def stem(token: str) -> str:
    t = token
    for suf in ("ions", "ion", "ings", "ing", "edly", "ed", "es", "s", "ly"):
        if len(t) > len(suf) + 3 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def tokenize(text: str) -> list[str]:
    out = []
    for w in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if w in STOPWORDS or len(w) < 2:
            continue
        out.append(stem(w))
    return out


def doc_id(rel: str) -> str:
    return hashlib.sha1(rel.encode("utf-8")).hexdigest()[:16]


def flatten_text(obj, skip_keys: set[str] | None = None) -> str:
    skip = skip_keys or {"path", "id"}
    parts: list[str] = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in skip:
                    continue
                walk(v)
        elif isinstance(x, list):
            for i in x:
                walk(i)
        elif isinstance(x, str):
            s = x.strip()
            if s:
                parts.append(s)
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            parts.append(str(x))

    walk(obj)
    return "\n".join(parts)


def title_of(rel: str, data: dict) -> str:
    for k in ("name", "title", "topic", "subject"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            if k == "subject" and data.get("grade"):
                return f"{data.get('grade')} {v}".strip()
            if k != "subject":
                return v.strip()
    approved = data.get("approved")
    if isinstance(approved, dict) and approved.get("title"):
        return str(approved["title"])
    return Path(rel).stem.replace("_", " ")


def iter_sources():
    for area in AREAS:
        base = ROOT / area
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.json")):
            if p.name in SKIP_NAMES:
                continue
            yield area, p


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    docs = []
    jsonl_by_area: dict[str, list] = defaultdict(list)

    for area, path in iter_sources():
        rel = path.relative_to(ROOT).as_posix()
        parts = path.relative_to(ROOT / area).parts
        level = parts[0] if parts else "General"
        data = json.loads(path.read_text(encoding="utf-8"))
        text = flatten_text(data)
        words = len(text.split()) if text.strip() else 0
        rec = {
            "id": doc_id(rel),
            "path": rel,
            "title": title_of(rel, data if isinstance(data, dict) else {}),
            "area": area,
            "level": level,
            "format": "json",
            "pages": None,
            "words": words,
            "chars": len(text),
            "scanned": False,
            "quality": "text" if words >= 80 else ("sparse" if words else "none"),
            "size": path.stat().st_size,
            "sha": hashlib.sha1(path.read_bytes()).hexdigest(),
            "hasOcr": False,
            "ocrPages": 0,
            "hasImages": False,
            "imageCount": 0,
            "images": [],
        }
        docs.append(rec)
        jsonl_by_area[area].append({
            "id": rec["id"],
            "path": rel,
            "title": rec["title"],
            "area": area,
            "level": level,
            "format": "json",
            "pages": None,
            "words": words,
            "text": text,
            "ocrText": "",
            "imageOcrText": "",
            "imageCount": 0,
        })

    docs.sort(key=lambda d: d["path"])
    by_q = Counter(d["quality"] for d in docs)
    catalog = {
        "count": len(docs),
        "generated": now,
        "totalTextChars": sum(d["chars"] for d in docs),
        "totalOcrChars": 0,
        "totalImageOcrChars": 0,
        "byQuality": dict(by_q),
        "documents": docs,
    }
    indexed = ROOT / "indexed"
    indexed.mkdir(exist_ok=True)
    (indexed / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    jsonl_dir = indexed / "_jsonl"
    jsonl_dir.mkdir(exist_ok=True)
    for area, rows in jsonl_by_area.items():
        dest = jsonl_dir / f"{area}.jsonl"
        dest.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    (indexed / "_convert_stats.json").write_text(json.dumps({
        "processed": len(docs),
        "byQuality": dict(by_q),
        "totalTextChars": catalog["totalTextChars"],
        "generated": now,
        "note": "JSON corpus index (post-flush). No PDFs.",
    }, indent=2) + "\n")

    # search
    index: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    search_docs = []
    for area, rows in jsonl_by_area.items():
        for body in rows:
            meta = next(d for d in docs if d["id"] == body["id"])
            search_docs.append({
                "id": body["id"],
                "path": body["path"],
                "title": body["title"],
                "area": body["area"],
                "level": body["level"],
                "format": "json",
                "pages": None,
                "quality": meta["quality"],
                "scanned": False,
                "words": body["words"],
                "hasOcr": False,
                "hasImages": False,
                "imageCount": 0,
            })
            for text, w in ((body["title"], 6.0), (body["text"], 2.0)):
                for tok in tokenize(text):
                    index[tok][body["id"]] += w

    search = ROOT / "search"
    search.mkdir(exist_ok=True)
    (search / "documents.json").write_text(json.dumps({
        "count": len(search_docs),
        "generated": now,
        "documents": search_docs,
    }, ensure_ascii=False) + "\n")
    inv = {tok: dict(post) for tok, post in index.items()}
    (search / "inverted.json").write_text(json.dumps({
        "count": len(inv),
        "generated": now,
        "index": inv,
    }, ensure_ascii=False) + "\n")

    print(f"indexed {len(docs)} json docs  quality={dict(by_q)}  terms={len(inv)}  chars={catalog['totalTextChars']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
