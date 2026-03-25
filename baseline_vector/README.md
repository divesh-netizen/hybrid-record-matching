# Baseline Vector Matching

This folder contains a very simple baseline experiment for the assignment.

## What it does

- reads PDFs from `Delivery Notes/` and `Purchase Invoices/`
- extracts crude text-like tokens from each PDF using only Python standard library
- builds a simple TF-IDF style vector representation
- computes cosine similarity between each invoice and each delivery note
- picks the top delivery note for each invoice
- evaluates top-1 accuracy using the shared filename prefix as provisional ground truth

## Important note

This is only a baseline experiment.

It is not a production matcher because:

- many PDFs appear image-heavy or scanned
- OCR is not being run here
- PDF parsing is intentionally lightweight
- filename prefix is used as a temporary label for evaluation

This is still useful because it shows:

- we started with a simple retrieval baseline
- we measured it
- we can compare it to a stronger second-stage approach later

## Run

From the assignment root:

```bash
python3 baseline_vector/vector_match_baseline.py
```

## Output

The script prints:

- top match for each purchase invoice
- similarity score
- whether the predicted match equals the provisional ground truth
- summary accuracy

It also writes:

- `baseline_vector/results.csv`
