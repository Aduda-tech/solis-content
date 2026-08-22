# search/ — full-text search index

Prebuilt search artifacts over the entire indexed corpus (2,787 documents,
including OCR text from scanned pages and OCR text from embedded images).

## Files

| File | Purpose |
|---|---|
| `documents.json` | Metadata for every document: `{id, path, title, area, level, format, pages, quality, scanned, words, hasOcr, hasImages, imageCount, images[]}`. Use for browsing/filtering and as the Fuse.js document list. |
| `inverted.json` | Inverted index: `token -> {docId: weight}`. Built from **title (×6) + text (×2) + OCR text + image OCR text**. Tokens are lowercased, stopword-filtered, lightly stemmed. Values are term weights. |

## How to use in a web app

### Option A — Server-side search (recommended, scales)

Load `inverted.json` into memory (or into Redis/Postgres/Mongo). For a query:

1. Tokenize the query (lowercase, split on non-alphanumerics, strip stopwords, stem like the index).
2. For each query token, look up `index[token]` → `{docId: weight}`.
3. Sum weights per document → rank → return top N doc IDs.
4. Fetch titles/paths from `documents.json` (or the per-doc JSON under `indexed/`) to render results.
5. Optionally add a prefix-search / typo-tolerance layer on top (or use Meilisearch/Typesense with `_jsonl/*.jsonl` for a zero-code hosted index).

### Option B — Client-side search (Fuse.js)

```html
<script src="https://cdn.jsdelivr.net/npm/fuse.js@7"></script>
<script>
  fetch('search/documents.json').then(r => r.json()).then(c => {
    const fuse = new Fuse(c.documents, {
      keys: [{ name: 'title', weight: 0.5 },
             { name: 'area', weight: 0.2 },
             { name: 'level', weight: 0.2 }],
      includeScore: true
    });
    // fuse.search("kcse biology 2025") -> ranked docs
  });
</script>
```
Fuse.js only searches metadata (title/area/level) — enough for fast filtering;
for deep full-text use Option A with `inverted.json` or index `_jsonl/*.jsonl`
into a hosted engine.

### Option C — Hosted engine (Elasticsearch/Meilisearch/Typesense)

Each line of `indexed/_jsonl/<area>.jsonl` is a ready-made document:
`{id, path, title, area, level, format, pages, words, text, ocrText, imageOcrText, imageCount}`.
Ingest directly — no transforms needed.

## Search coverage

- Full extracted text (2,688 documents `quality: text`)
- **OCR text from scanned pages** (`ocrText`) — 342 documents, ~4.7M characters
- **OCR text from embedded images / diagrams** (`imageOcrText`, `images[].ocrText`)
  — 289 documents, 1,964 images (figures in exam papers, notes, diagrams)
- 11 corrupt PDFs have no extractable text (listed in catalog as `quality: none`)

## Stemming note

The index applies a light suffix-stripping stemmer (s/es/ed/ing/ion(s)/ly).
For best recall, apply the same normalization to queries, or use a proper
stemmer (Porter) when building a server-side copy.
