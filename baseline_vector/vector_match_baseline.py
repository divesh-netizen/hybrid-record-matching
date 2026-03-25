from __future__ import annotations

import csv
import math
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_DIR = ROOT / "Delivery Notes"
INVOICE_DIR = ROOT / "Purchase Invoices"
RESULTS_CSV = Path(__file__).resolve().parent / "results.csv"


TOKEN_RE = re.compile(r"[a-z0-9]{3,}")
PRINTABLE_RE = re.compile(rb"[A-Za-z0-9][A-Za-z0-9 .,:;/_()#&-]{2,}")


def label_from_path(path: Path) -> str:
    name = path.stem
    return name.split(".", 1)[0].strip()


def readable_name(path: Path) -> str:
    return path.name


def extract_pdf_text_tokens(path: Path) -> list[str]:
    data = path.read_bytes()

    # Baseline extraction only: collect printable byte runs from the raw PDF.
    # This is noisy, but good enough for a first-pass retrieval experiment.
    text_chunks = [match.decode("latin1", errors="ignore") for match in PRINTABLE_RE.findall(data)]

    # Include filename text as a weak hint so the baseline can leverage
    # document naming patterns when present.
    text_chunks.append(path.stem.replace(".", " "))

    text = " ".join(text_chunks).lower()
    return TOKEN_RE.findall(text)


def build_document_term_counts(paths: list[Path]) -> dict[Path, Counter]:
    doc_counts: dict[Path, Counter] = {}
    for path in paths:
        tokens = extract_pdf_text_tokens(path)
        doc_counts[path] = Counter(tokens)
    return doc_counts


def compute_idf(doc_counts: dict[Path, Counter]) -> dict[str, float]:
    total_docs = len(doc_counts)
    doc_freq: Counter = Counter()

    for counts in doc_counts.values():
        for term in counts:
            doc_freq[term] += 1

    idf: dict[str, float] = {}
    for term, freq in doc_freq.items():
        idf[term] = math.log((1 + total_docs) / (1 + freq)) + 1.0

    return idf


def tfidf_vector(term_counts: Counter, idf: dict[str, float]) -> dict[str, float]:
    if not term_counts:
        return {}

    total_terms = sum(term_counts.values())
    vector: dict[str, float] = {}
    for term, count in term_counts.items():
        tf = count / total_terms
        vector[term] = tf * idf.get(term, 1.0)
    return vector


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0

    shared_terms = set(vec_a).intersection(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in shared_terms)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def main() -> None:
    delivery_paths = sorted(DELIVERY_DIR.glob("*.pdf"))
    invoice_paths = sorted(INVOICE_DIR.glob("*.pdf"))

    if not delivery_paths or not invoice_paths:
        raise SystemExit("Could not find PDF files in the expected folders.")

    all_paths = delivery_paths + invoice_paths
    doc_counts = build_document_term_counts(all_paths)
    idf = compute_idf(doc_counts)
    vectors = {path: tfidf_vector(doc_counts[path], idf) for path in all_paths}

    results: list[dict[str, str]] = []

    for invoice_path in invoice_paths:
        scored = []
        for delivery_path in delivery_paths:
            score = cosine_similarity(vectors[invoice_path], vectors[delivery_path])
            scored.append((score, delivery_path))

        scored.sort(key=lambda item: item[0], reverse=True)
        best_score, best_match = scored[0]

        gold_label = label_from_path(invoice_path)
        predicted_label = label_from_path(best_match)
        is_correct = gold_label == predicted_label

        results.append(
            {
                "invoice_file": readable_name(invoice_path),
                "gold_label": gold_label,
                "predicted_delivery_file": readable_name(best_match),
                "predicted_label": predicted_label,
                "similarity": f"{best_score:.4f}",
                "correct_top1": "yes" if is_correct else "no",
            }
        )

    correct = sum(1 for row in results if row["correct_top1"] == "yes")
    total = len(results)
    accuracy = correct / total if total else 0.0

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
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    print("Baseline vector matching results")
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
    print("Ground truth here is provisional and based on shared filename labels.")


if __name__ == "__main__":
    main()
