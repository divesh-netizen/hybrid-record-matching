from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path

import fitz
import numpy as np
import pdfplumber
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_DIR = ROOT / "Delivery Notes"
INVOICE_DIR = ROOT / "Purchase Invoices"
RESULTS_CSV = Path(__file__).resolve().parent / "results.csv"

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "180"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "40"))
MIN_TEXT_LENGTH = int(os.getenv("MIN_TEXT_LENGTH", "40"))

TOKEN_RE = re.compile(r"\S+")
NORMALIZE_RE = re.compile(r"\s+")


@dataclass
class DocumentData:
    path: Path
    label: str
    raw_text: str
    chunks: list[str]
    avg_embedding: np.ndarray | None = None


def label_from_path(path: Path) -> str:
    return path.stem.split(".", 1)[0].strip()


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = NORMALIZE_RE.sub(" ", text)
    return text.strip()


def extract_with_pypdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def extract_with_pdfplumber(path: Path) -> str:
    try:
        parts = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def extract_with_pymupdf(path: Path) -> str:
    try:
        parts = []
        with fitz.open(str(path)) as pdf:
            for page in pdf:
                parts.append(page.get_text("text") or "")
        return "\n".join(parts)
    except Exception:
        return ""


def extract_text(path: Path) -> str:
    candidates = [
        extract_with_pymupdf(path),
        extract_with_pdfplumber(path),
        extract_with_pypdf(path),
    ]
    best = max(candidates, key=lambda text: len(text or ""))
    return normalize_text(best)


def chunk_text(text: str, chunk_words: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = TOKEN_RE.findall(text)
    if not words:
        return []

    if len(words) <= chunk_words:
        return [" ".join(words)]

    step = max(1, chunk_words - overlap)
    chunks = []
    for start in range(0, len(words), step):
        end = start + chunk_words
        chunk_words_list = words[start:end]
        if not chunk_words_list:
            continue
        chunk = " ".join(chunk_words_list)
        if len(chunk) >= MIN_TEXT_LENGTH:
            chunks.append(chunk)
        if end >= len(words):
            break
    return chunks


def load_documents(folder: Path) -> list[DocumentData]:
    docs = []
    for path in sorted(folder.glob("*.pdf")):
        raw_text = extract_text(path)
        chunks = chunk_text(raw_text)
        docs.append(
            DocumentData(
                path=path,
                label=label_from_path(path),
                raw_text=raw_text,
                chunks=chunks,
            )
        )
    return docs


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def embed_documents(model: SentenceTransformer, docs: list[DocumentData]) -> None:
    for doc in docs:
        if not doc.chunks:
            doc.avg_embedding = None
            continue

        embeddings = model.encode(
            doc.chunks,
            batch_size=16,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        doc.avg_embedding = embeddings.mean(axis=0)
        norm = np.linalg.norm(doc.avg_embedding)
        if norm != 0:
            doc.avg_embedding = doc.avg_embedding / norm


def cosine_similarity(vec_a: np.ndarray | None, vec_b: np.ndarray | None) -> float:
    if vec_a is None or vec_b is None:
        return 0.0
    return float(np.dot(vec_a, vec_b))


def main() -> None:
    print(f"Loading model on CPU: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    delivery_docs = load_documents(DELIVERY_DIR)
    invoice_docs = load_documents(INVOICE_DIR)

    print(f"Delivery notes loaded: {len(delivery_docs)}")
    print(f"Purchase invoices loaded: {len(invoice_docs)}")
    print("")

    print("Extraction summary")
    for doc in invoice_docs + delivery_docs:
        print(
            f"{doc.path.name} | chars={len(doc.raw_text)} | chunks={len(doc.chunks)}"
        )
    print("")

    embed_documents(model, delivery_docs)
    embed_documents(model, invoice_docs)

    results: list[dict[str, str]] = []

    for invoice in invoice_docs:
        scored = []
        for delivery in delivery_docs:
            score = cosine_similarity(invoice.avg_embedding, delivery.avg_embedding)
            scored.append((score, delivery))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_match = scored[0]
        correct = invoice.label == best_match.label

        results.append(
            {
                "invoice_file": invoice.path.name,
                "gold_label": invoice.label,
                "predicted_delivery_file": best_match.path.name,
                "predicted_label": best_match.label,
                "similarity": f"{best_score:.4f}",
                "correct_top1": "yes" if correct else "no",
                "invoice_chars": str(len(invoice.raw_text)),
                "invoice_chunks": str(len(invoice.chunks)),
                "delivery_chars": str(len(best_match.raw_text)),
                "delivery_chunks": str(len(best_match.chunks)),
            }
        )

    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "invoice_file",
                "gold_label",
                "predicted_delivery_file",
                "predicted_label",
                "similarity",
                "correct_top1",
                "invoice_chars",
                "invoice_chunks",
                "delivery_chars",
                "delivery_chunks",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    correct = sum(1 for row in results if row["correct_top1"] == "yes")
    total = len(results)
    accuracy = correct / total if total else 0.0

    print("Embedding baseline results")
    print(f"Invoices evaluated: {total}")
    print(f"Top-1 correct: {correct}")
    print(f"Top-1 accuracy: {accuracy:.2%}")
    print("")

    for row in results:
        status = "OK" if row["correct_top1"] == "yes" else "MISS"
        print(
            f"{status:4} | invoice={row['invoice_file']} | "
            f"pred={row['predicted_delivery_file']} | "
            f"score={row['similarity']}"
        )

    print("")
    print(f"Detailed results written to: {RESULTS_CSV}")
    print("Evaluation labels are provisional and based on shared filename prefixes.")


if __name__ == "__main__":
    main()
