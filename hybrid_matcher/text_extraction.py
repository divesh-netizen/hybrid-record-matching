from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import fitz
import pdfplumber
from pypdf import PdfReader


NORMALIZE_SPACES_RE = re.compile(r"[ \t]+")
TOKEN_RE = re.compile(r"\S+")


@dataclass
class ExtractedText:
    path: Path
    text: str
    lines: list[str]
    chunks: list[str]


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r", "\n")
    normalized_lines = []
    for line in text.splitlines():
        line = NORMALIZE_SPACES_RE.sub(" ", line).strip()
        if line:
            normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def extract_with_pymupdf(path: Path) -> str:
    try:
        with fitz.open(path) as pdf:
            return "\n".join(page.get_text("text") or "" for page in pdf)
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


def extract_with_pypdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def extract_text(path: Path) -> ExtractedText:
    candidates = [
        extract_with_pymupdf(path),
        extract_with_pdfplumber(path),
        extract_with_pypdf(path),
    ]
    best_text = max(candidates, key=lambda value: len(value or ""))
    normalized = normalize_text(best_text)
    lines = normalized.splitlines() if normalized else []
    chunks = chunk_text(normalized)
    return ExtractedText(path=path, text=normalized, lines=lines, chunks=chunks)


def chunk_text(text: str, chunk_words: int = 180, overlap: int = 40) -> list[str]:
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
        chunks.append(" ".join(chunk_words_list))
        if end >= len(words):
            break
    return chunks
