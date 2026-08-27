# search/

Inverted index over the JSON corpus.

Query: lowercase, split `[a-z0-9]+`, drop stopwords and tokens shorter than 2, stem `ions/ion/ings/ing/edly/ed/es/s/ly`, look up `inverted.json.index[token]`, sum weights per `docId`.

Weights baked in at build time: title ×6, body ×2.
