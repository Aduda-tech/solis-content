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


def docx_text(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception:
        return ""


# ─── Title cleaning for scraped downloads ─────────────────────────────
# The arena docx files were scraped from the web and their filenames carry
# Google-Drive/WordPress residue ("1ByiY2GRUH r Download 1 Download 2 a href
# https drive google"). Those leak into search results as garbage titles.
# clean_title() derives a human-readable title from the document text when
# the filename title is residue, and only falls back to scrubbing the
# filename when the text yields nothing.

SCRAP_TOKENS = re.compile(
    r"\b(?:a\s*href|a\s*hre|href|https?://|www|drive|google|com\s*uc\s*expo|uc\s*expo|"
    r"target\s*blank|rel\s*noopener|noopener|wp\s*[- ]?block|wp\s*[- ]?content|"
    r"p\s*class|li\s*class|class\s*has|has\s*inline|inline\s*color|color\s*rgba|"
    r"rgba|span\s*style|open|blank|download|down|strong|img|div|arrow|mbs|ms)\b",
    re.I,
)
LEAD_ID = re.compile(r"^(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{8,}\b\s*", re.I)
GOOD_LINE = re.compile(r"[A-Za-z]{4}")
HEADER_SKIP = re.compile(
    r"^(page\s*\d+|name|date|level|school|class|teacher|admission|instructions?|time|"
    r"total\s*marks?|candidate|index\s*number|signature|jina|nambari|code\s*:|"
    r"kenya\s*certificate|section\s*[a-z])",
    re.I,
)
GRADE_RE = re.compile(
    r"\b(grade\s*[0-9]|form\s*[1-4]|pp\s*[12]?|pre[\s-]*primary|primary|junior\s*school|senior\s*school)\b",
    re.I,
)
SUBJECT_RE = re.compile(
    r"\b(mathematics|maths|english|kiswahili|swahili|science|physics|chemistry|biology|"
    r"agriculture|cre|christian|religious|ire|islamic|history|geography|business|"
    r"home\s*science|computer|music|art|creative|french|german|arabic|technical|"
    r"social\s*studies|hygiene|environment|indigenous|hindu|literacy|numeracy|"
    r"composition|grammar|knec|kjsea|kicd|curriculum|scheme|schemes)\b",
    re.I,
)


def _has_residue(title: str) -> bool:
    return bool(LEAD_ID.search(title)) or bool(SCRAP_TOKENS.search(title))


def _title_from_text(text: str) -> str:
    lines: list[str] = []
    for raw in (text or "").split("\n"):
        s = re.sub(r"\s+", " ", raw).strip()
        if not s or len(s) > 60:
            continue
        if LEAD_ID.match(s) or SCRAP_TOKENS.search(s):
            continue
        if re.fullmatch(r"page\s*\d+(\s*of\s*\d+)?", s, re.I):
            continue
        if re.fullmatch(r"table\s+of\s+contents", s, re.I):
            continue
        if not GOOD_LINE.search(s):
            continue
        lines.append(s)
        if len(lines) >= 12:
            break
    subject_line = grade_line = first = None
    for s in lines:
        if HEADER_SKIP.match(s):
            continue
        if first is None:
            first = s
        if subject_line is None and SUBJECT_RE.search(s) and len(s.split()) <= 8:
            subject_line = s
        if grade_line is None and GRADE_RE.search(s) and len(s.split()) <= 6:
            grade_line = s
    if subject_line and grade_line and subject_line != grade_line:
        return f"{subject_line} – {grade_line}"[:110]
    if subject_line:
        return subject_line[:110]
    if grade_line:
        return grade_line[:110]
    return first[:110] if first else ""


def _scrub_title(title: str) -> str:
    t = re.sub(r"\s+", " ", SCRAP_TOKENS.sub(" ", LEAD_ID.sub(" ", title))).strip(" \t,;:-.()")
    t = " ".join(
        w for w in t.split()
        if w.lower() not in ("a", "p", "hre", "er", "ng", "ht", "pdf", "docx", "in", "to", "of", "and", "the")
    )
    return t


def clean_title(title: str, text: str) -> str:
    """Return a human-readable title for a scraped docx, or the title unchanged."""
    if not _has_residue(title):
        return title[:120]
    derived = _title_from_text(text)
    if derived and len(derived) >= 8 and len(derived.split()) >= 2:
        return derived
    scrubbed = _scrub_title(title)
    return scrubbed[:120] if len(scrubbed) >= 8 else title[:120]


def iter_sources():
    # Structured folders hold JSON documents AND, since the corpus was
    # re-organised, relocated .docx files (exams, lesson-notes, lesson-plans,
    # schemes-of-work). Both are indexed; the folder's first level is the
    # grade ("Grade 7", "Form 4", ...).
    for area in AREAS:
        base = ROOT / area
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.json")):
            if p.name in SKIP_NAMES:
                continue
            yield area, p, "json"
        for p in sorted(base.rglob("*.docx")):
            yield area, p, "docx"
    # Remaining raw scrapes (curriculum-design source PDFs, KJSEA design
    # PDFs) live under downloads/arena and keep their subfolder as the area.
    arena = ROOT / "downloads" / "arena"
    if arena.is_dir():
        for p in sorted(arena.rglob("*.docx")):
            area = p.relative_to(arena).parts[0]
            yield area, p, "docx"


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    docs = []
    jsonl_by_area: dict[str, list] = defaultdict(list)

    for area, path, fmt in iter_sources():
        rel = path.relative_to(ROOT).as_posix()
        try:
            parts = path.relative_to(ROOT / area).parts
            level = parts[0] if parts else "General"
        except ValueError:
            parts = path.relative_to(ROOT / "downloads" / "arena").parts
            level = parts[1] if len(parts) > 1 else "General"
        if fmt == "json":
            data = json.loads(path.read_text(encoding="utf-8"))
            text = flatten_text(data)
            title = title_of(rel, data if isinstance(data, dict) else {})
        else:
            text = docx_text(path)[:80000]
            raw_title = re.sub(r"-+", " ", re.sub(r"^\d+-", "", path.stem)).strip()[:120] or path.stem
            title = clean_title(raw_title, text)
        words = len(text.split()) if text.strip() else 0
        rec = {
            "id": doc_id(rel),
            "path": rel,
            "title": title,
            "area": area,
            "level": str(level),
            "format": fmt,
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
            "format": fmt,
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
