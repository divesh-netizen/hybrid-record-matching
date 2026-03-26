# Document AI / OCR Options

This note compares the main OCR and document-understanding options that can be used in the final heterogeneous matching architecture.

The main question is:

"How do we turn PDFs, images, Excel files, CSVs, and Word documents into usable text, tables, layout, and structured evidence for matching?"

## Quick comparison

| Option | What it is | Best for | Tables / layout | Cost style | Good fit for our architecture |
|---|---|---|---|---|---|
| Azure Document Intelligence | Microsoft cloud document AI service | enterprise OCR, forms, invoices, layout extraction | strong | paid, usage-based | very good |
| Google Document AI | Google cloud document AI platform | OCR, form parsing, custom document processors | strong | paid, usage-based | very good |
| AWS Textract | AWS OCR and document extraction API | OCR, tables, forms, expense and ID extraction | strong | paid, usage-based | very good |
| ABBYY | enterprise OCR / IDP platform | high-volume enterprise document workflows | strong | paid, usually sales-led | very good |
| Tesseract | open-source OCR engine | local OCR, low-cost OCR, prototypes | limited compared to cloud document AI | free | useful as fallback |
| OCRmyPDF | open-source OCR PDF wrapper using Tesseract | making scanned PDFs searchable | limited layout understanding | free | very useful preprocessing step |

## 1. Azure Document Intelligence

### What it is

Azure Document Intelligence is Microsoft’s cloud service for OCR and document understanding.

It can extract:

- text
- key-value pairs
- tables
- layout
- invoices
- receipts
- IDs
- custom document fields

### How it works

- upload or send a document
- Azure processes it
- returns structured JSON output

### Best use cases

- enterprise document pipelines
- invoices and forms
- layout-aware table extraction
- workflows where custom extraction is needed later

### Cost

- paid
- generally usage-based by pages / model usage
- Azure also has limited free usage for trying it

### Why it is useful for our architecture

It is strong for:

- scanned PDFs
- layout extraction
- key-value extraction
- tables spanning business documents

This makes it a strong option for the ingestion + extraction layers.

Official links:

- https://learn.microsoft.com/azure/ai-services/document-intelligence/
- https://azure.microsoft.com/en-us/pricing/details/ai-document-intelligence

## 2. Google Document AI

### What it is

Google Document AI is Google Cloud’s document understanding platform.

It supports:

- OCR
- layout parsing
- form parsing
- specialized processors
- custom extractors

### How it works

- choose a processor type
- send the document
- receive structured extraction results

### Best use cases

- large-scale document processing
- custom processors
- form-heavy and table-heavy extraction
- teams already using GCP

### Cost

- paid
- usage-based per page / processor

### Why it is useful for our architecture

It is a good fit when we need:

- OCR
- table parsing
- structured extraction at scale
- custom extraction pipelines later

Official links:

- https://cloud.google.com/document-ai
- https://cloud.google.com/document-ai/pricing

## 3. AWS Textract

### What it is

AWS Textract is Amazon’s OCR and document extraction service.

It supports:

- OCR text extraction
- tables
- forms
- expense extraction
- ID extraction
- signatures

### How it works

- call Textract APIs with a document
- receive structured text / table / field output

### Best use cases

- AWS-first stacks
- invoice / expense workflows
- table and form extraction
- API-driven document processing

### Cost

- paid
- usage-based
- AWS usually offers a limited free tier for early testing

### Why it is useful for our architecture

It is strong for:

- OCR
- forms
- tables
- structured output in cloud workflows

Official links:

- https://aws.amazon.com/textract/
- https://aws.amazon.com/textract/pricing/

## 4. ABBYY

### What it is

ABBYY is a long-established enterprise OCR and intelligent document processing platform.

It is more than basic OCR.
It is often used for:

- document classification
- extraction
- validation
- workflow automation

### How it works

- documents go through OCR and document understanding workflows
- extraction and validation logic can be configured
- often used with human review and operational workflows

### Best use cases

- high-volume enterprise document operations
- difficult scans
- many languages
- document-heavy business process automation

### Cost

- paid
- usually quote-based / sales-led pricing

### Why it is useful for our architecture

ABBYY is a strong fit if the final system becomes:

- high-volume
- compliance-heavy
- validation-heavy
- more of an enterprise document operations platform

Official links:

- https://www.abbyy.com/ai-document-processing/
- https://www.abbyy.com/vantage/

## 5. Tesseract

### What it is

Tesseract is an open-source OCR engine.

It mainly converts scanned text images into machine-readable text.

### How it works

- run locally
- pass image or scanned page
- receive OCR text output

### Best use cases

- low-cost OCR
- local processing
- offline workflows
- experimentation and prototypes

### Cost

- free
- open source

### Limitations

- weaker than full document AI platforms for:
  - layout understanding
  - table structure
  - form extraction
  - enterprise-scale robustness

### Why it is useful for our architecture

Good as:

- fallback OCR
- local OCR engine
- building a lower-cost preprocessing layer

Official links:

- https://github.com/tesseract-ocr

## 6. OCRmyPDF

### What it is

OCRmyPDF is an open-source tool that adds an OCR text layer to scanned PDFs.

It uses Tesseract behind the scenes.

### How it works

- input a scanned PDF
- OCRmyPDF creates a searchable PDF with embedded text

### Best use cases

- batch OCR preprocessing for scanned PDFs
- making PDFs searchable before downstream parsing
- improving simple PDF pipelines at low cost

### Cost

- free
- open source

### Limitations

- it is mainly a preprocessing tool
- it is not a full document understanding platform

### Why it is useful for our architecture

Very useful as a first OCR layer when:

- PDFs are scanned
- cost matters
- we want to keep a local pipeline

Official links:

- https://ocrmypdf.readthedocs.io/en/stable/introduction.html
- https://github.com/ocrmypdf/OCRmyPDF

## Recommended use in our architecture

### If we want the strongest cloud-first setup

Use one of:

- Azure Document Intelligence
- Google Document AI
- AWS Textract

These are best for:

- OCR
- layout extraction
- table extraction
- structured parsing at scale

### If we want enterprise document operations

Use:

- ABBYY

This is strongest when the solution grows into a larger business workflow platform.

### If we want a lower-cost / local-first setup

Use:

- OCRmyPDF
- Tesseract

This is best as:

- fallback OCR
- preprocessing
- prototype path

## My practical recommendation

For the final architecture in this assignment, I would position the options like this:

- primary cloud OCR / document AI: `Azure Document Intelligence` or `Google Document AI`
- AWS-native option: `AWS Textract`
- enterprise-heavy option: `ABBYY`
- low-cost fallback: `OCRmyPDF + Tesseract`

## Short summary

If the goal is a serious production matching platform, cloud document-AI vendors are the strongest primary choice because they provide OCR plus layout and table understanding. If the goal is a cheaper or local-first prototype, Tesseract and OCRmyPDF are very useful but should be seen mainly as OCR and preprocessing tools rather than full document understanding systems.
