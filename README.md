# solis-content

Structured Kenyan CBC JSON for **Solis School Manager**: schemes of work, exams, lesson notes/plans, revision, and teacher-approved learning docs.

The large PDF/OCR mirror that previously lived here was reset. This tree is the **JSON corpus** on `main` (`c6d7684` and later). Search/catalog artifacts are rebuilt from these files only.

## Layout

| Path | What |
|---|---|
| `manifest.json` | Nested Grade → Subject → Term index (what School Manager `lookupContent` reads) |
| `schemes-of-work/Grade {7,8,9}/…/Term 3/scheme-of-work.json` | Term 3 schemes (weekly breakdown) |
| `exams/`, `lesson-notes/`, `lesson-plans/`, `revision/` | Sample Grade 7 Mathematics JSON |
| `learning-docs/` | Teacher-approved exam-builder payloads from School Manager |
| `indexed/catalog.json` | Flat catalog for browse/filter |
| `indexed/_jsonl/<area>.jsonl` | Full-text lines for search engines |
| `search/documents.json` + `search/inverted.json` | Prebuilt inverted index |
| `tools/build_index.py` | Regenerates catalog + search from JSON on disk |

## Rebuild the index

```bash
python3 tools/build_index.py
```

Tokenizer matches School Manager’s planned client: lowercase `[a-z0-9]+`, English stopwords, light suffix stem, weights **title×6 + text×2**.

## Fetch (pin a SHA)

```
https://raw.githubusercontent.com/Aduda-tech/solis-content/<sha>/indexed/catalog.json
https://raw.githubusercontent.com/Aduda-tech/solis-content/<sha>/search/inverted.json
```

No Git LFS in this tree (no raster assets).
