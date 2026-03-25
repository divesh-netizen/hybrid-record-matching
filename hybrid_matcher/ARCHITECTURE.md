# Hybrid Matcher Architecture

This file explains the final architecture for the hybrid batch matcher.

The goal is simple:

- we have one batch of purchase invoices
- we have one batch of delivery notes
- for each invoice, we want to find the best delivery-note match
- we want to explain why that match was chosen
- we want to show a match percentage so the result is easy to review

This is not just a similarity search.
It is a batch matching pipeline with retrieval, field checks, reranking, and explanation output.

## 1. What problem this architecture solves

The product problem is:

"Given two collections of business documents, find which records correspond to each other."

This is difficult because:

- the two sides may use different formats
- field names may differ
- some PDFs are noisy or partially scanned
- one side may contain invoice language while the other contains delivery-note language
- not every pair has a clean exact-text match

So we should not depend on one signal only.

That is why the final architecture is hybrid:

- text similarity helps us find likely candidates
- business fields help us confirm or reject candidates
- explanations make the result auditable for a human

## 2. Why hybrid instead of only embeddings

If we only use embeddings or text similarity:

- two unrelated invoices from similar suppliers may look close
- OCR noise may distort wording
- delivery notes may not contain the same totals as invoices
- some very strong business signals like reference numbers may get diluted

So the better design is:

1. use text retrieval to narrow the search
2. use business heuristics to rerank candidates
3. output reasons and confidence

This gives a result that is more practical and easier to trust.

## 3. Final pipeline

The final hybrid pipeline has five stages.

### Stage 1: Batch input

Input:

- all files in `Purchase Invoices/`
- all files in `Delivery Notes/`

Why:

- the actual product is batch-to-batch checking
- the user is not comparing only one invoice and one note
- the system must search across the whole opposite collection

### Stage 2: Reliable text extraction

File:

- `hybrid_matcher/text_extraction.py`

What it does:

- reads every PDF
- tries multiple extractors:
  - `pymupdf`
  - `pdfplumber`
  - `pypdf`
- keeps the best text version
- normalizes spaces and lines
- creates chunks for retrieval-style comparison

Why:

- PDF text quality varies a lot
- one parser may work better than another on a given file
- using more than one extractor makes the pipeline more robust

### Stage 3: Field extraction heuristics

File:

- `hybrid_matcher/field_extraction.py`

What it extracts:

- document number
- reference numbers
- primary date
- total amount
- company name
- line-like business text fragments

Why:

- these are the business signals that help decide whether two documents really belong together
- they are usually more reliable than generic text similarity

This stage uses regex plus lightweight heuristics.
It is intentionally simple and explainable.

### Stage 4: Candidate retrieval

File:

- `hybrid_matcher/hybrid_matcher.py`

What it does:

- builds a retrieval vector for every document
- compares each invoice against all delivery notes
- keeps only the top candidate set

Why:

- in batch matching, comparing every feature deeply against every document is expensive and noisy
- retrieval gives us a shortlist first
- then we spend more logic only on the most likely candidates

In this environment the retrieval backend is TF-IDF style text similarity.
In a stronger production version, this stage can be replaced with sentence embeddings.

### Stage 5: Reranking and explanation

File:

- `hybrid_matcher/hybrid_matcher.py`

What it does:

- takes the top retrieval candidates
- scores them again using business signals
- picks the best final match
- writes reasons and confidence-style output

Why:

- this is where the architecture becomes hybrid
- retrieval finds likely candidates
- reranking decides which candidate makes the most business sense

## 4. Scoring parameters in the results file

The results CSV has many columns because we want the result to be explainable.
Each score is a signal used by the matcher.

Think of it like this:

- some columns are identity fields
- some columns are match signals
- some columns are extracted evidence
- some columns are human-readable explanations

Below is what each important field means.

### Identity and prediction columns

`invoice_file`

- the invoice being evaluated

`gold_label`

- the temporary expected label based on the shared filename prefix
- only used for rough evaluation in this assignment

`predicted_delivery_file`

- the delivery note selected as the best match

`predicted_label`

- the label from the selected delivery note filename

`correct_top1`

- whether the predicted file matches the temporary filename-based label
- this is only a provisional benchmark, not a production truth source

### Final output columns

`match_type`

- the decision bucket:
  - `match`
  - `possible_match`
  - `partial_match`
  - `unmatched`

Why it exists:

- not every result should be a hard yes/no
- this makes ambiguity visible

`final_score`

- the combined score after all hybrid signals are applied

Why it exists:

- this is the internal ranking score used to choose the best candidate

`match_percentage`

- the same final score shown as a percentage-like confidence value

Why it exists:

- easier for humans to read in Excel or a review UI
- gives a quick sense of strength of match

Important note:

- this is a practical confidence indicator
- it is not yet a statistically calibrated probability

### Retrieval signal

`retrieval_score`

- how similar the invoice and delivery note are at the overall text level

What it means:

- high value means the documents look similar in content

Why it exists:

- useful as the first broad signal
- helps surface likely candidates even when exact field extraction is incomplete

### Business-field signals

`document_number_score`

- checks whether extracted document numbers match exactly

What it means:

- strong direct identifier signal when available

Why it exists:

- document numbers can be very strong evidence of linkage

`reference_score`

- checks overlap of extracted business references
- examples:
  - customer order number
  - order ref
  - reference codes like `16108-178668-MY`

What it means:

- high value means both documents refer to the same business reference

Why it exists:

- usually one of the strongest matching signals in these documents

`company_score`

- similarity of company or supplier name

What it means:

- high value means supplier/company wording is similar across both files

Why it exists:

- helps distinguish documents from different vendors

`date_score`

- how close the extracted dates are

What it means:

- exact date match is strongest
- small day difference still gives partial support

Why it exists:

- invoice and delivery dates are often close even if not identical

`amount_score`

- whether extracted totals are close

What it means:

- strong when both sides contain usable totals and they align

Why it exists:

- invoices often contain totals that can validate a candidate

Important note:

- delivery notes do not always contain the same amount information
- so this signal is useful when present but should not dominate

`line_score`

- overlap between line-like fragments or item descriptions

What it means:

- strong when item text looks similar between the two documents

Why it exists:

- item text can confirm the business relationship even when other fields are noisy

## 5. Evidence columns

These columns are there so a human reviewer can inspect what the system extracted.

`invoice_document_number`

- document number extracted from the invoice

`delivery_document_number`

- document number extracted from the delivery note

`invoice_company`

- company-like text extracted from the invoice

`delivery_company`

- company-like text extracted from the delivery note

`invoice_primary_date`

- main parsed date from the invoice

`delivery_primary_date`

- main parsed date from the delivery note

`invoice_total_amount`

- extracted invoice total when found

`delivery_total_amount`

- extracted delivery-note amount when found

`shared_references`

- reference values found on both sides

Why these evidence columns exist:

- they make the result auditable
- they help a reviewer understand what the model actually used
- they make debugging much easier

## 6. Explanation column

`reasons`

- human-readable explanation of why the candidate was selected

Examples:

- `reference overlap: 16108-178668-MY`
- `dates match exactly`
- `company names are very similar`
- `line-item text overlaps strongly`

Why it exists:

- users should not have to infer the reasoning from raw scores
- this improves trust and usability

## 7. Why there are many parameters in Excel

There are many parameters because this architecture is trying to do three things at once:

1. make a decision
2. justify the decision
3. expose the evidence behind the decision

So the CSV is not only a prediction file.
It is also:

- a review file
- a debugging file
- an explainability file

If this were a product UI, the user would not need to see every raw column at once.

A cleaner UI could show only:

- invoice
- best delivery note
- match percentage
- match type
- top reasons

And then let the user expand the row to see the detailed evidence fields.

## 8. Why this architecture is a good assignment answer

This architecture shows:

- clear problem framing
- practical decomposition
- hybrid reasoning instead of one-model-only thinking
- awareness of ambiguity
- explainability
- auditability
- a path toward production improvements

It also fits the assignment request well because it answers:

- what the system does
- why each part exists
- how results are explained
- how a user would review matches

## 9. What I would say as the short final summary

"The final architecture is a batch hybrid matcher. It first extracts usable text from both document collections, then pulls likely business fields, uses text retrieval to find candidate matches, reranks them with business rules, and returns the best match with reasons and a confidence percentage. The extra parameters in the CSV are there to make the result explainable and auditable rather than a black-box score."
