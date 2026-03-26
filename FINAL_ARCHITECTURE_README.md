# Final Architecture For Heterogeneous Bucket Matching

This document describes the next-stage architecture for matching Bucket A with Bucket B when:

- file types can be PDF, Excel, CSV, image, or Word
- fields are unknown
- values are unknown
- matches can be `1:1`, `1:M`, `M:1`, or `M:M`
- evidence may exist at document level, row level, or aggregate level

This is the broader version of the problem beyond the current PDF-focused hybrid matcher in this repository.

## Problem framing

This should be treated as a **hierarchical matching and reconciliation problem**, not only as file similarity.

Why:

- some files are free-form documents
- some files are structured tables
- some matches happen at whole-document level
- some matches happen at row level
- some matches happen only through totals or grouped values
- explicit references may be missing

So the system needs to reason over multiple units:

- document
- section
- table
- row
- row group
- summary / total block

## Final goal

The final goal is:

1. ingest all files from Bucket A and Bucket B
2. extract text, layout, tables, and metadata
3. create a shared internal representation
4. generate candidates across document, row, and aggregate levels
5. score and reconcile candidates
6. return explainable matches with confidence and review support

## High-level architecture

The final architecture has eight layers:

1. ingestion and file routing
2. content extraction and OCR
3. structural understanding
4. canonical representation
5. candidate generation
6. multi-level matching and reconciliation
7. global assignment / graph reasoning
8. human review and audit

## 1. Ingestion and file routing

### What it does

- accepts files from Bucket A and Bucket B
- detects type and routes each file to the correct parser
- stores raw file and processing metadata

### File types

- PDF
- scanned PDF
- image
- Excel
- CSV
- Word document

### Why it matters

- each format needs a different extraction path
- traceability from raw file to final decision is important

## 2. Content extraction and OCR

### Goal

Get the best machine-readable content from each file.

### Strategy

For text PDFs and Word documents:

- native text extraction
- preserve page and section boundaries

For scanned PDFs and images:

- OCR with layout awareness
- preserve block, line, and page positions

For Excel and CSV:

- preserve workbook, sheet, row, column, and cell structure

### Vendors / tools

Good options:

- Azure Document Intelligence
- Google Document AI
- AWS Textract
- ABBYY
- Tesseract / OCRmyPDF as lower-cost fallback

## 3. Structural understanding

### Goal

Understand the content shape, not just raw text.

### Detect

- headings
- key-value sections
- paragraphs
- tables
- table headers
- totals and subtotals
- multi-page table continuation

### Important special case

Tables may span multiple pages and only show headers on the first page.

So the system should stitch tables across pages using:

- column alignment
- row pattern consistency
- page adjacency
- similar surrounding context

## 4. Canonical representation

### Goal

Represent extracted information in one flexible internal model, even when schemas are unknown.

### Canonical object types

- `document_entity`
- `table_entity`
- `row_entity`
- `group_entity`
- `summary_entity`
- `person_entity`
- `organization_entity`
- `transaction_entity`
- `aggregate_entity`

### Canonical evidence types

- names
- dates
- addresses
- IDs / references
- document numbers
- amounts
- quantities
- descriptions
- date ranges
- totals

### Why this matters

The system needs a shared representation to compare:

- scanned IDs
- payroll PDFs
- CSV transaction rows
- report tables

even when their schemas look unrelated.

## 5. Candidate generation

### Goal

Generate a shortlist of plausible matches before deeper scoring.

### Candidate levels

- document to document
- document to row
- row to row
- document to row group
- row group to summary
- aggregate to aggregate

### Signals

- lexical retrieval
- semantic retrieval with embeddings
- amount proximity
- date overlap
- entity overlap
- structural context similarity

### Why this matters

- avoids expensive exhaustive deep comparison
- allows the later stages to focus on plausible candidates

## 6. Multi-level matching and reconciliation

This is the core matching layer.

### Match levels

#### Whole-document match

Useful when both files represent the same record directly.

#### Row-level match

Useful when a row inside a report is the true match target.

#### Group-level match

Useful when many detailed rows match one summary object.

#### Aggregate match

Useful when there are no direct references and only totals align.

### Scoring signals

Each candidate should be scored using a weighted combination of:

- text similarity
- entity overlap
- name similarity
- date closeness
- amount similarity
- quantity similarity
- row-content similarity
- table-context similarity
- aggregate reconciliation quality
- OCR confidence
- extraction quality

### Important design principle

Not every match type will use the same signals.

Examples:

- scanned driving license to payroll row:
  - name match
  - date-of-birth match
  - address overlap

- payroll monthly total to four CSV rows:
  - period overlap
  - grouped rows sum to the monthly total
  - employee or account context matches

## 7. Global assignment and graph reasoning

### Why local top-1 is not enough

If every object simply picks its best candidate independently, we can create contradictions.

Examples:

- one row matched to two different summaries
- one summary matched to the wrong set of component rows
- inconsistent matches across the batch

### Better approach

Treat the full matching task as a constrained graph / reconciliation problem.

Nodes:

- documents
- rows
- groups
- aggregates

Edges:

- possible match
- supporting evidence
- aggregate-to-components relationship

### Techniques

- bipartite matching for `1:1`
- constrained optimization for `1:M` and `M:1`
- graph clustering for related groups
- reconciliation search over row subsets

## 8. Human review and audit

### Goal

The system should produce decisions a user can inspect and trust.

### Output should include

- matched objects
- match type
- confidence
- extracted evidence
- reconciliation logic
- ambiguity flags
- OCR / extraction warnings

### Review states

- auto-match
- needs review
- ambiguous
- unmatched
- rejected

## Techniques to combine

This should be a hybrid architecture, not a one-model system.

### OCR / document AI

Use for:

- scanned files
- layout extraction
- forms and tables

### Embeddings

Use for:

- semantic retrieval
- candidate generation under schema mismatch

### Heuristic and typed field extraction

Use for:

- references
- names
- dates
- totals
- identifiers

### LLM-assisted interpretation

Use for:

- unknown field-name interpretation
- weird long-tail documents
- explanation generation

Important note:

I would not use an LLM as the only matcher.
I would use it on top of structured evidence and deterministic checks.

### Reconciliation engine

Use for:

- grouped row matching
- aggregate balancing
- period-level matching

This is the key requirement for `1:M`, `M:1`, and `M:M`.

## Confidence strategy

Confidence should combine:

- evidence strength
- evidence consistency
- extraction quality
- uniqueness of the candidate
- gap over the next-best candidate
- success of reconciliation

So confidence is not just one similarity number.

## Failure modes to plan for

- OCR errors
- missing table headers on later pages
- duplicate names
- duplicate totals
- merged spreadsheet cells
- inconsistent date formats
- one file containing multiple logical records
- low-quality scans

The system should surface uncertainty instead of forcing a bad match.

## How to upgrade the current hybrid matcher into this final architecture

The current hybrid matcher already gives us a good starting point:

- text extraction
- heuristic field extraction
- retrieval
- reranking
- explanation output

To reach the final goal, I would upgrade it in stages.

### Stage 1: expand file support

Current:

- mostly PDF focused

Upgrade:

- add Excel, CSV, Word, and image ingestion
- route each file type through the right parser

### Stage 2: move to hierarchical objects

Current:

- one main result per document

Upgrade:

- represent documents, tables, rows, groups, and totals separately

### Stage 3: improve table understanding

Current:

- line-fragment heuristics

Upgrade:

- proper table extraction
- multi-page table stitching
- row-level normalization

### Stage 4: richer entity extraction

Current:

- references, dates, totals, company names, line fragments

Upgrade:

- names
- addresses
- IDs
- date ranges
- account-like fields
- summary totals

### Stage 5: stronger retrieval

Current:

- simple retrieval plus heuristic reranking

Upgrade:

- lexical + embedding hybrid retrieval
- retrieval at document, row, and group levels

### Stage 6: add reconciliation engine

Current:

- best match per invoice

Upgrade:

- support grouped row-to-summary matching
- support total balancing
- support `1:M`, `M:1`, and `M:M`

### Stage 7: add global consistency

Current:

- local ranking only

Upgrade:

- constrained assignment
- graph-based consistency

### Stage 8: improve human review

Current:

- CSV output with reasons

Upgrade:

- review UI
- side-by-side evidence
- explicit approval / rejection / regrouping workflow

## Why this is the right final direction

This architecture is strong because it:

- handles unknown schemas
- handles many file types
- supports document, row, and aggregate matching
- supports non-`1:1` relationships
- remains explainable
- supports human review

## Short final summary

The final system should be a hierarchical hybrid matching and reconciliation platform for heterogeneous document buckets. It should ingest many file types, extract text and structure, create canonical entities, generate candidates across document and row levels, reconcile them with semantic and aggregate evidence, and return globally consistent, explainable matches. The current hybrid matcher in this repository is a solid document-level starting point, and the path forward is to extend it into a multi-level reconciliation system.
