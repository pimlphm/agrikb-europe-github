from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.doc_parser import parse_document


TRIGGER_MAP = {
    "symptom": ["symptom", "现象", "症状", "异常", "vibration", "alarm"],
    "cause": ["cause", "原因", "导致", "because", "failure due to"],
    "rule": ["rule", "若", "if", "when", "criteria", "判据"],
    "action": ["action", "建议", "检查", "replace", "mitigate", "inspect"],
    "evidence": ["evidence", "case", "案例", "record", "test", "log"],
}


@dataclass
class DiagnosticChunk:
    chunk_id: str
    chunk_type: str
    text: str
    entities: list[str]
    conditions: list[str]
    relations: list[dict]
    source: str
    metadata: dict

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "chunk_type": self.chunk_type,
            "text": self.text,
            "entities": self.entities,
            "conditions": self.conditions,
            "relations": self.relations,
            "source": self.source,
            "metadata": self.metadata,
        }


def sentence_split(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def token_count(text: str) -> int:
    return len(re.findall(r"[\w\u4e00-\u9fff]+", text))


def lexical_overlap(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", left.lower()))
    right_tokens = set(re.findall(r"[\w\u4e00-\u9fff]+", right.lower()))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def classify_text(text: str) -> str:
    lowered = text.lower()
    for chunk_type, markers in TRIGGER_MAP.items():
        if any(marker.lower() in lowered for marker in markers):
            return chunk_type
    return "evidence"


def extract_conditions(text: str) -> list[str]:
    patterns = [
        r"(?:after|before|during)\s+[^,.;\n]+",
        r"(?:启动后|停机后|运行中|负载[^\s,.;]+|温度[^\s,.;]+|转速[^\s,.;]+)",
        r"\b\d+\s*(?:min|minutes|ms|rpm|°c|c|v|a)\b",
    ]
    conditions = []
    for pattern in patterns:
        conditions.extend(match.group(0).strip() for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return list(dict.fromkeys(conditions))


def structure_split(text: str) -> list[str]:
    blocks = []
    current = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        heading_like = stripped.startswith("#") or re.match(r"^\d+(\.\d+)*\s", stripped)
        if heading_like and current:
            blocks.append("\n".join(current).strip())
            current = [stripped]
        else:
            current.append(stripped)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def merge_chunks(chunks: list[DiagnosticChunk], min_tokens: int, max_tokens: int) -> list[DiagnosticChunk]:
    if not chunks:
        return []

    merged = []
    buffer = chunks[0]
    for current in chunks[1:]:
        if token_count(buffer.text) < min_tokens and buffer.chunk_type == current.chunk_type:
            buffer = DiagnosticChunk(
                chunk_id=buffer.chunk_id,
                chunk_type=buffer.chunk_type,
                text=buffer.text + "\n" + current.text,
                entities=list(dict.fromkeys(buffer.entities + current.entities)),
                conditions=list(dict.fromkeys(buffer.conditions + current.conditions)),
                relations=[],
                source=buffer.source,
                metadata=dict(buffer.metadata),
            )
            buffer.metadata["tokens"] = token_count(buffer.text)
            continue
        merged.append(buffer)
        buffer = current
    merged.append(buffer)

    final_chunks = []
    for item in merged:
        if token_count(item.text) <= max_tokens:
            final_chunks.append(item)
            continue
        sentences = sentence_split(item.text)
        start = 0
        while start < len(sentences):
            current_sentences = []
            while start < len(sentences) and token_count(" ".join(current_sentences + [sentences[start]])) <= max_tokens:
                current_sentences.append(sentences[start])
                start += 1
            if not current_sentences:
                current_sentences.append(sentences[start])
                start += 1
            split_text = " ".join(current_sentences).strip()
            cloned = DiagnosticChunk(
                chunk_id=f"{item.chunk_id}_part{len(final_chunks)+1}",
                chunk_type=item.chunk_type,
                text=split_text,
                entities=item.entities,
                conditions=item.conditions,
                relations=[],
                source=item.source,
                metadata=dict(item.metadata),
            )
            cloned.metadata["tokens"] = token_count(split_text)
            final_chunks.append(cloned)
    return final_chunks


def segment_parsed_document(parsed_document: dict, config: dict | None = None) -> list[dict]:
    config = config or {}
    ingestion = config.get("ingestion", {})
    min_tokens = ingestion.get("min_chunk_tokens", 150)
    max_tokens = ingestion.get("max_chunk_tokens", 500)
    threshold = ingestion.get("semantic_boundary_threshold", 0.45)

    doc_name = parsed_document["name"]
    doc_id = Path(doc_name).stem
    text = parsed_document.get("content", "")
    blocks = structure_split(text)
    chunks: list[DiagnosticChunk] = []
    counter = 1

    for block in blocks:
        sentences = sentence_split(block)
        if not sentences:
            continue
        current_sentences = [sentences[0]]
        current_type = classify_text(sentences[0])

        for sentence in sentences[1:]:
            sentence_type = classify_text(sentence)
            similarity = lexical_overlap(current_sentences[-1], sentence)
            boundary = sentence_type != current_type or (
                similarity < threshold and sentence_type in {"symptom", "cause", "rule", "action"}
            )
            if boundary:
                chunk_text = " ".join(current_sentences).strip()
                chunks.append(
                    DiagnosticChunk(
                        chunk_id=f"{doc_id}_{counter:04d}",
                        chunk_type=current_type,
                        text=chunk_text,
                        entities=[],
                        conditions=extract_conditions(chunk_text),
                        relations=[],
                        source=doc_name,
                        metadata={
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page": None,
                            "tokens": token_count(chunk_text),
                        },
                    )
                )
                counter += 1
                current_sentences = [sentence]
                current_type = sentence_type
            else:
                current_sentences.append(sentence)

        chunk_text = " ".join(current_sentences).strip()
        chunks.append(
            DiagnosticChunk(
                chunk_id=f"{doc_id}_{counter:04d}",
                chunk_type=current_type,
                text=chunk_text,
                entities=[],
                conditions=extract_conditions(chunk_text),
                relations=[],
                source=doc_name,
                metadata={
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "page": None,
                    "tokens": token_count(chunk_text),
                },
            )
        )
        counter += 1

    return [item.to_dict() for item in merge_chunks(chunks, min_tokens, max_tokens)]


def segment_document(file_path: str, config: dict | None = None) -> list[dict]:
    parsed_document = parse_document(file_path)
    if not parsed_document:
        return []
    return segment_parsed_document(parsed_document, config=config)
