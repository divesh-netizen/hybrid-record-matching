# Hybrid Matcher

This is the final batch matching version for the assignment.

The main idea is:

- we have one batch of purchase invoices
- we have one batch of delivery notes
- for each invoice, we try to find the best matching delivery note
- we return the best match with reasons and a match percentage

This is closer to the actual product shape than a simple one-to-one document comparison.

## What it does

The script:

1. reads all PDFs from `Purchase Invoices/` and `Delivery Notes/`
2. extracts usable text using multiple PDF parsers
3. extracts likely business fields with simple heuristics
4. builds retrieval vectors from document text
5. gets top candidate delivery notes for each invoice
6. reranks those candidates using business signals
7. outputs the best match, match type, reasons, and percentage

## Business signals used

The reranking currently uses:

- document number match
- reference number overlap
- company name similarity
- date closeness
- amount comparison when available
- line text overlap
- overall text retrieval similarity

## Why this is useful

This is useful because vector similarity alone is not enough.

Two documents can look similar in text but still not be the true business match.
So here we use text similarity as one signal, then strengthen the decision with field checks.

## Output

The script writes:

- `hybrid_matcher/results.csv`

Each row is for one invoice and includes:

- predicted best delivery note
- match type
- final score
- match percentage
- reasons
- extracted dates, document numbers, companies, and totals when found

Example style of explanation:

- `reference overlap: 16108-178668-MY`
- `dates match exactly`
- `company names are very similar`
- `line-item text overlaps strongly`

## Match labels

Current labels are:

- `match`
- `possible_match`
- `partial_match`
- `unmatched`

This helps show confidence more clearly instead of only saying yes or no.

## Run

From the assignment root:

```bash
./.venv/bin/python hybrid_matcher/hybrid_matcher.py
```

## Important note

This is still a practical prototype, not a production-ready matcher.

Some PDFs are noisy and some appear scanned or OCR-like.
So a next upgrade would be:

- OCR for image-heavy PDFs
- better field extraction
- better candidate generation
- stronger confidence calibration
- UI review flow for ambiguous matches

## Product framing

If I describe this in simple words:

"We take two batches of documents, compare every invoice against likely delivery-note candidates, then return the best match with reasons and a confidence percentage."

That is the main thing this version is trying to show.
