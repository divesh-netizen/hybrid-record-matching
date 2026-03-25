# Simple Matching Approach Notes

## What this assignment is asking

We have two collections of documents:

- `Delivery Notes`
- `Purchase Invoices`

The goal is not just to compare one pair of documents.
The goal is to help a user match records across the two collections:

- which invoice matches which delivery note
- which records do not match
- which records are ambiguous
- why the system believes that

This is more like "match documents across two sets" than "upload two files and answer yes/no".

## Simple baseline idea

A practical first baseline is:

1. Extract text from both document sets
2. Convert each document into a vector embedding
3. Compare documents using vector similarity
4. Use the best similarity score to propose candidate matches

This is a reasonable starting point because it is fast to build and gives us an initial signal.

## Why vector similarity alone is not enough

Vector similarity is useful, but it should not be the only matching method.

Problems:

- two different invoices may look textually similar
- scanned PDFs may have OCR errors
- delivery notes and invoices may describe the same transaction in different wording
- some important fields may be missing on one side
- overall text similarity may miss the actual business relationship

So embeddings should be treated as one signal, not the whole solution.

## Better practical approach

Use a hybrid approach:

1. Extract text with OCR or PDF parsing
2. Extract important fields when possible
3. Use vector similarity as one feature
4. Add rule-based checks on important business fields
5. Return a match result with explanation

## Important fields to compare

Examples of useful fields:

- company or supplier name
- invoice number
- delivery note number
- reference number or PO number
- date
- line item names
- quantities
- subtotal / total amount

These fields are usually more reliable than raw text similarity alone.

## Example matching logic

For each invoice:

1. Compare it against delivery notes
2. Use vector similarity to find top candidate notes
3. Re-rank those candidates with business rules:
   - similar company name
   - close date
   - similar quantity
   - similar line items
   - matching reference number
4. Classify result as:
   - `match`
   - `possible_match`
   - `partial_match`
   - `unmatched`

## Example output to user

Instead of only saying "matched", explain why:

- supplier names are similar
- dates are 1 day apart
- 3 line items overlap
- total amount is close
- reference number appears on both documents

This makes the system more trustworthy and auditable.

## Simple summary

My current thinking is:

"Start with OCR/text extraction, use vector similarity to get likely candidates, then use business-field checks to make the final decision and explain the reason."

