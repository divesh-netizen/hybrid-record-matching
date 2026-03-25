# Record Matching Assignment

This repository contains my take-home assignment work for matching records across two document collections:

- `Purchase Invoices/`
- `Delivery Notes/`

The main product idea is batch checking.

That means:

- we have one batch of invoices
- we have one batch of delivery notes
- for each invoice, we try to find the best matching delivery note
- we return the best match with reasons and a match percentage

## What is in this repo

### `baseline_vector/`

This is the first simple baseline.

It uses a lightweight TF-IDF style vector built from crude PDF text extraction.
This was mainly to create a very simple retrieval starting point.

### `embedding_baseline/`

This is the second baseline.

It uses better PDF text extraction and a stronger semantic matching approach.
This gives a better retrieval signal than the first baseline.

### `hybrid_matcher/`

This is the final direction and the main version I would present.

It combines:

- reliable text extraction
- heuristic field extraction
- document retrieval
- reranking using business signals
- explanation output

This folder includes:

- `README.md`
- `ARCHITECTURE.md`
- `hybrid_matcher.py`
- helper modules

## Final approach

The final approach is a hybrid batch matcher.

High level flow:

1. read all PDFs from both collections
2. extract usable text
3. extract likely business fields
4. retrieve likely candidate matches
5. rerank candidates using business signals
6. output best match with reasons and percentage

This is more useful than pure text similarity alone because document matching is not only a semantic search problem.
Business references, dates, company names, document numbers, and line-item overlap also matter.

## Current output

The hybrid matcher writes a results file with:

- best matched delivery note for each invoice
- match type
- match percentage
- individual score components
- extracted evidence fields
- human-readable reasons

## Run

From the repository root:

```bash
python3 baseline_vector/vector_match_baseline.py
./.venv/bin/python hybrid_matcher/hybrid_matcher.py
```

If needed, the embedding baseline can also be run from the same root.

## Notes

- this is a practical prototype, not a production-ready system
- filename-based labels are used only as a temporary evaluation shortcut
- the hybrid version is the main final architecture for the assignment

## What I would do next

With another 1 to 2 weeks, I would:

- improve OCR and text extraction for noisy PDFs
- strengthen field extraction
- use stronger embedding retrieval
- improve confidence calibration
- add a cleaner human review flow for ambiguous matches
