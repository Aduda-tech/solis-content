# solis-content

Learning & teaching content repository ΓÇö originally hosting structured (JSON) curriculum content, now extended with a **free-download mirror of Teachers Arena (arena.co.ke)** materials as PDF/DOC documents.

## Repository structure

| Folder | Contents |
|---|---|
| `revision/` | **KCSE** 2005ΓÇô2017 (171) ┬╖ **KCPE** 2000ΓÇô2017 (137) ┬╖ **KPSEA** G6 (47) ┬╖ **KJSEA** G9 (25) ┬╖ KCPE 2022 w/ schemes (13) | 414 |
| `exams/` | Form 1ΓÇô4 exams & marking schemes (by Form) ┬╖ KNEC SBA (G3ΓÇô9) ┬╖ KNEC primary tests ┬╖ holiday homework | 463 |
| `lesson-notes/` | Primary (Class 4ΓÇô8) ┬╖ CBC (G1ΓÇô6) ┬╖ Junior Secondary + JSS teacher training ┬╖ Secondary F1ΓÇô4 by subject | 323 |
| `schemes-of-work/` | CBC schemes G1ΓÇô6 ΓÇö all subjects, Terms 1ΓÇô3 | 313 |
| `curriculum-designs/` | CBC designs G1ΓÇô9 + syllabi + combined designs | 141 |
| `lesson-plans/` | CBC lesson plans PP1ΓÇôPP2 & G1ΓÇô6 | 56 |
| `forms/` | TSC ┬╖ KNEC exams ┬╖ MOE schools ┬╖ scholarships & loans ┬╖ other | 124 |
| `professional-docs/` | CBC resources (report books, rubrics, IEP, templates, teacher professionalism) ┬╖ KNEC briefing | 127 |
| `manifest.json` | Index of native JSON content + `pdfMaterials` summary of the pushed document mirror |

## Notes
- Documents are PDF unless noted (a few `.doc`/`.docx` as published on the source site).
- 4 source files are unavailable on arena.co.ke itself (dead links / Drive-restricted) and are listed in `manifest.json ΓåÆ pdfMaterials.unavailableFiles`.

## Education News Hub mirror (second batch)

| Folder | Added |
|---|---|
| `exams/` | 23 |
| `lesson-notes/` | 36 |
| `schemes-of-work/` | 34 |

Source: educationnewshub.co.ke free downloads (PP1-PP2 schemes, Grade 1-10 notes/schemes/exams, Form 3-4 exams). See "educationnewshubMaterials" in manifest.json.

## Third batch (educationnewshub + newsblaze + teacher.co.ke mirror)

| Folder | Added |
|---|---|
| `exams/` | 464 |
| `schemes-of-work/` | 111 |
| `lesson-notes/` | 93 |
| `revision/` | 91 |
| `curriculum-designs/` | 2 |

Sources: educationnewshub.co.ke (Form 3-4 exams & marking schemes, PP1-PP2 exams,
Grade 1-10 schemes/notes, 2025-2026 editions), newsblaze.co.ke (Grade 7 CBC set),
teacher.co.ke (direct PDFs: syllabi, Grade 10 assessments, 2025 KCSE/KJSEA papers,
topical revision). See "batch3Materials" in manifest.json for the unavailable-file list.

## indexed/ — machine-readable corpus

Every document in the repo has been converted to JSON with cleaned, searchable
text (2,787 docs, ~104M characters):

| Location | Contents |
|---|---|
| `indexed/<area>/<level>/<name>.json` | one JSON per document (metadata + clean full text) |
| `indexed/catalog.json` | metadata for all documents (browsing/filtering) |
| `indexed/_jsonl/<area>.jsonl` | full-text bulk feeds (JSON Lines) for search engines |
| `indexed/README.md` | schema + usage guide |

Ad-like content (site watermarks, contact info, social CTAs, repeated
headers/footers) was removed; document content is preserved otherwise. 121
image-only scanned PDFs have no text layer yet (OCR is a follow-up). See
`indexed/README.md` for details.
