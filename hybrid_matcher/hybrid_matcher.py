from __future__ import annotations

import csv
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz

try:
    from hybrid_matcher.field_extraction import ExtractedFields, company_similarity, extract_fields
    from hybrid_matcher.text_extraction import ExtractedText, extract_text
except ModuleNotFoundError:
    from field_extraction import ExtractedFields, company_similarity, extract_fields
    from text_extraction import ExtractedText, extract_text


ROOT = Path(__file__).resolve().parents[1]
DELIVERY_DIR = ROOT / "Delivery Notes"
INVOICE_DIR = ROOT / "Purchase Invoices"
RESULTS_CSV = Path(__file__).resolve().parent / "results.csv"

MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
TOP_K = int(os.getenv("TOP_K_CANDIDATES", "5"))
RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "tfidf").lower()
TOKEN_RE = re.compile(r"[A-Za-z0-9]{2,}")


@dataclass
class DocumentRecord:
    path: Path
    label: str
    extracted: ExtractedText
    fields: ExtractedFields
    retrieval_vector: dict[str, float] | None = None


def label_from_path(path: Path) -> str:
    return path.stem.split(".", 1)[0].strip()


def load_records(folder: Path) -> list[DocumentRecord]:
    records = []
    for path in sorted(folder.glob("*.pdf")):
        extracted = extract_text(path)
        fields = extract_fields(extracted.text, extracted.lines)
        records.append(
            DocumentRecord(
                path=path,
                label=label_from_path(path),
                extracted=extracted,
                fields=fields,
            )
        )
    return records


def build_retrieval_vectors(records: list[DocumentRecord]) -> None:
    token_counts: dict[Path, Counter[str]] = {}
    doc_freq: Counter[str] = Counter()

    for record in records:
        tokens = TOKEN_RE.findall(record.extracted.text.lower())
        counts = Counter(tokens)
        token_counts[record.path] = counts
        for term in counts:
            doc_freq[term] += 1

    total_docs = len(records)
    idf = {
        term: math.log((1 + total_docs) / (1 + freq)) + 1.0
        for term, freq in doc_freq.items()
    }

    for record in records:
        counts = token_counts[record.path]
        total_terms = sum(counts.values()) or 1
        record.retrieval_vector = {
            term: (count / total_terms) * idf.get(term, 1.0)
            for term, count in counts.items()
        }


def cosine_similarity(left: dict[str, float] | None, right: dict[str, float] | None) -> float:
    if left is None or right is None:
        return 0.0
    shared_terms = set(left).intersection(right)
    if not shared_terms:
        return 0.0
    dot = sum(left[term] * right[term] for term in shared_terms)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def score_candidate(invoice: DocumentRecord, delivery: DocumentRecord) -> dict[str, float | list[str] | str]:
    reasons: list[str] = []

    retrieval_score = cosine_similarity(invoice.retrieval_vector, delivery.retrieval_vector)
    final_score = 0.35 * retrieval_score

    document_number_score = 0.0
    if (
        invoice.fields.document_number
        and delivery.fields.document_number
        and invoice.fields.document_number == delivery.fields.document_number
    ):
        document_number_score = 1.0
        final_score += 0.20 * document_number_score
        reasons.append(f"document numbers match: {invoice.fields.document_number}")

    reference_overlap = sorted(
        set(invoice.fields.reference_numbers + invoice.fields.reference_tokens)
        & set(delivery.fields.reference_numbers + delivery.fields.reference_tokens)
    )
    if reference_overlap:
        ref_score = 1.0
        final_score += 0.30 * ref_score
        reasons.append(f"reference overlap: {', '.join(reference_overlap[:2])}")
    else:
        ref_score = 0.0

    company_score = company_similarity(invoice.fields.company_name, delivery.fields.company_name)
    if company_score > 0:
        final_score += 0.10 * company_score
        if company_score >= 0.8:
            reasons.append("company names are very similar")
        elif company_score >= 0.6:
            reasons.append("company names are somewhat similar")

    date_score = 0.0
    if invoice.fields.primary_date and delivery.fields.primary_date:
        delta_days = abs((invoice.fields.primary_date - delivery.fields.primary_date).days)
        if delta_days == 0:
            date_score = 1.0
            reasons.append("dates match exactly")
        elif delta_days <= 3:
            date_score = 0.7
            reasons.append(f"dates are close ({delta_days} days apart)")
        elif delta_days <= 10:
            date_score = 0.3
        final_score += 0.08 * date_score

    amount_score = 0.0
    if invoice.fields.total_amount is not None and delivery.fields.total_amount is not None:
        max_amount = max(invoice.fields.total_amount, delivery.fields.total_amount, 1.0)
        relative_gap = abs(invoice.fields.total_amount - delivery.fields.total_amount) / max_amount
        if relative_gap <= 0.02:
            amount_score = 1.0
            reasons.append("amounts are nearly identical")
        elif relative_gap <= 0.10:
            amount_score = 0.6
            reasons.append("amounts are reasonably close")
        final_score += 0.04 * amount_score

    line_score = line_overlap_score(invoice.fields.line_fragments, delivery.fields.line_fragments)
    if line_score > 0:
        final_score += 0.03 * line_score
        if line_score >= 0.7:
            reasons.append("line-item text overlaps strongly")
        elif line_score >= 0.4:
            reasons.append("some line-item text overlaps")

    if retrieval_score >= 0.75:
        reasons.append("text similarity is high")
    elif retrieval_score >= 0.60:
        reasons.append("text similarity is moderately high")

    if not reasons:
        reasons.append("match is driven mostly by overall text similarity")

    return {
        "final_score": round(final_score, 4),
        "retrieval_score": round(retrieval_score, 4),
        "document_number_score": round(document_number_score, 4),
        "reference_score": round(ref_score, 4),
        "company_score": round(company_score, 4),
        "date_score": round(date_score, 4),
        "amount_score": round(amount_score, 4),
        "line_score": round(line_score, 4),
        "reasons": reasons,
        "match_type": classify_match(final_score, reference_overlap, date_score, line_score),
    }


def line_overlap_score(invoice_lines: list[str], delivery_lines: list[str]) -> float:
    if not invoice_lines or not delivery_lines:
        return 0.0
    best = 0.0
    for left in invoice_lines[:5]:
        for right in delivery_lines[:5]:
            score = fuzz.token_set_ratio(left, right) / 100.0
            if score > best:
                best = score
    return best


def classify_match(final_score: float, reference_overlap: list[str], date_score: float, line_score: float) -> str:
    if final_score >= 0.78 and (reference_overlap or date_score >= 0.7 or line_score >= 0.7):
        return "match"
    if final_score >= 0.62:
        return "possible_match"
    if final_score >= 0.45:
        return "partial_match"
    return "unmatched"


def main() -> None:
    delivery_records = load_records(DELIVERY_DIR)
    invoice_records = load_records(INVOICE_DIR)
    all_records = delivery_records + invoice_records
    build_retrieval_vectors(all_records)

    print(f"Delivery notes loaded: {len(delivery_records)}")
    print(f"Purchase invoices loaded: {len(invoice_records)}")
    print(f"Retrieval backend: {RETRIEVAL_BACKEND}")
    print("")

    results: list[dict[str, str]] = []

    for invoice in invoice_records:
        candidate_scores = [
            (cosine_similarity(invoice.retrieval_vector, delivery.retrieval_vector), delivery)
            for delivery in delivery_records
        ]
        candidate_scores.sort(key=lambda item: item[0], reverse=True)
        top_candidates = candidate_scores[:TOP_K]

        reranked = []
        for _, delivery in top_candidates:
            detail = score_candidate(invoice, delivery)
            reranked.append((float(detail["final_score"]), delivery, detail))

        reranked.sort(key=lambda item: item[0], reverse=True)
        best_score, best_match, detail = reranked[0]
        correct = invoice.label == best_match.label

        results.append(
            {
                "invoice_file": invoice.path.name,
                "gold_label": invoice.label,
                "predicted_delivery_file": best_match.path.name,
                "predicted_label": best_match.label,
                "correct_top1": "yes" if correct else "no",
                "match_type": str(detail["match_type"]),
                "final_score": f"{best_score:.4f}",
                "match_percentage": f"{min(max(best_score, 0.0), 1.0) * 100:.2f}",
                "retrieval_score": f"{float(detail['retrieval_score']):.4f}",
                "document_number_score": f"{float(detail['document_number_score']):.4f}",
                "reference_score": f"{float(detail['reference_score']):.4f}",
                "company_score": f"{float(detail['company_score']):.4f}",
                "date_score": f"{float(detail['date_score']):.4f}",
                "amount_score": f"{float(detail['amount_score']):.4f}",
                "line_score": f"{float(detail['line_score']):.4f}",
                "invoice_document_number": invoice.fields.document_number or "",
                "delivery_document_number": best_match.fields.document_number or "",
                "invoice_company": invoice.fields.company_name or "",
                "delivery_company": best_match.fields.company_name or "",
                "invoice_primary_date": invoice.fields.primary_date.isoformat() if invoice.fields.primary_date else "",
                "delivery_primary_date": best_match.fields.primary_date.isoformat() if best_match.fields.primary_date else "",
                "invoice_total_amount": f"{invoice.fields.total_amount:.2f}" if invoice.fields.total_amount is not None else "",
                "delivery_total_amount": f"{best_match.fields.total_amount:.2f}" if best_match.fields.total_amount is not None else "",
                "shared_references": " | ".join(
                    sorted(
                        set(invoice.fields.reference_numbers + invoice.fields.reference_tokens)
                        & set(best_match.fields.reference_numbers + best_match.fields.reference_tokens)
                    )
                ),
                "reasons": " | ".join(detail["reasons"]),
            }
        )

    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(results[0].keys()) if results else [],
        )
        writer.writeheader()
        writer.writerows(results)

    correct = sum(row["correct_top1"] == "yes" for row in results)
    total = len(results)
    accuracy = correct / total if total else 0.0

    print("Hybrid matching results")
    print(f"Invoices evaluated: {total}")
    print(f"Top-1 correct: {correct}")
    print(f"Top-1 accuracy: {accuracy:.2%}")
    print("")

    for row in results:
        status = "OK" if row["correct_top1"] == "yes" else "MISS"
        print(
            f"{status:4} | invoice={row['invoice_file']} | pred={row['predicted_delivery_file']} | "
            f"type={row['match_type']} | score={row['final_score']} | match={row['match_percentage']}%"
        )

    print("")
    print(f"Detailed results written to: {RESULTS_CSV}")
    print("Evaluation labels are provisional and based on shared filename prefixes.")


if __name__ == "__main__":
    main()
