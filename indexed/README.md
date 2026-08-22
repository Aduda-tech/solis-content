# indexed/ — machine-readable corpus

Every document in this repository has been converted to a **JSON document with
clean, searchable text**. The original files are untouched; this folder is an
additional, index-friendly representation for web apps, search engines and LLM
pipelines.

## Layout

```
indexed/
├── <area>/<level>/<document-name>.pdf.json     one JSON per source document
├── catalog.json                                 metadata for all 2,787 documents
├── _jsonl/<area>.jsonl                          full-text bulk feed (JSON Lines, per area)
├── _convert_stats.json                          conversion statistics
└── README.md
```

## Per-document JSON schema

```jsonc
{
  "id": "16-char sha1 of relative path",     // stable identifier
  "path": "revision/KCSE/2025 KCSE BIOLOGY PP1.pdf",   // original file path
  "title": "2025 KCSE BIOLOGY PP1",          // cleaned title (no watermark/ads)
  "area": "revision",                        // top-level folder
  "level": "KCSE",                           // level/grade/class/form
  "format": "pdf",                           // pdf | docx | pptx | doc
  "size": 123456,                            // original file size (bytes)
  "sha": "git blob sha of original file",
  "pages": 44,                               // page count (PDFs)
  "scanned": false,                          // true = image-only scan (no text layer)
  "quality": "text",                         // text | sparse | rough | none
  "words": 8853,
  "chars": 51428,
  "linesRemoved": 12,                        // ad/watermark lines stripped
  "shortLinesDropped": 284,                  // blank/very short lines collapsed
  "extractNote": "optional",                 // extraction notes (mislabeled formats, etc.)
  "text": "REPUBLIC OF KENYA ..."            // cleaned full text
}
```

## catalog.json

Array of all documents with metadata **only** (no text) — ideal for browsing,
filtering and building a search UI. Same fields as above minus `text`.

## _jsonl/<area>.jsonl

One JSON object per line with `{id, path, title, area, level, format, pages,
words, text}` — ready to stream into Elasticsearch / Meilisearch / Typesense /
OpenSearch / a Postgres tsvector column / any JSONL ingest pipeline.

## Data quality

- **2,411** documents fully extracted as text (`quality: text`)
- **232** `sparse` (partially text, partly image pages) and **23** `rough`
  (legacy `.doc` via strings extraction)
- **121** `scanned` documents are image-only scans (no text layer) — `text`
  is empty; the original PDF remains available for viewing. OCR can be run as
  a follow-up pass (≈3,900 pages).
- **0** extraction errors — 12 mislabeled files (PPTX/DOCX named `.pdf`) were
  re-extracted by content type.
- Ad-like content removed: site watermarks (`teacher.co.ke`, `kcserevision.com`,
  `educationnewshub`, `newsblaze`, `teachers arena`), contact details (phone,
  email), social-media/CTA lines, repeated page footers/headers. Content is
  otherwise preserved verbatim (only whitespace normalized).

## Using in a web app

1. Fetch `catalog.json` → show list/filter UI (area, level, subject).
2. Fetch the per-document JSON (e.g. `indexed/revision/KCSE/….json`) → render `text`.
3. For full-text search, index `_jsonl/*.jsonl` server-side, or load the JSONs
   into a client-side index (Fuse.js/Lunr) using `catalog.json` + `_jsonl`.

## Regenerating

Conversion is deterministic. Rerun `python3 convert.py --resume` after adding
documents, then `python3 build_catalog.py` to refresh `catalog.json` and the
JSONL feeds.
