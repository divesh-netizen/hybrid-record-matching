# Embedding Baseline

This is the second baseline for the assignment.

It is stronger than the crude token-vector baseline because it:

- extracts text from PDFs using real PDF parsers
- chunks document text into smaller sections
- embeds those chunks with a sentence-transformer model
- compares documents using semantic similarity

## CPU-friendly setup

This script is written for CPU usage.

Default model:

- `sentence-transformers/all-MiniLM-L6-v2`

That model is small, commonly used, and reasonable for a quick baseline on CPU.

## What it does

1. Read all PDFs from both collections
2. Extract text using multiple PDF parsers
3. Chunk the text into overlapping windows
4. Create embeddings for each chunk
5. Aggregate chunk similarity into a document-to-document score
6. Pick the best delivery note for each purchase invoice
7. Evaluate top-1 accuracy using the shared filename prefix as provisional labels

## Run

```bash
uv run python embedding_baseline/embedding_match_baseline.py
```

## Output

The script writes:

- `embedding_baseline/results.csv`

And prints:

- extraction stats
- top-1 predictions
- accuracy summary


