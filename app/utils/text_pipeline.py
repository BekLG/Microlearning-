def clean_text(raw: str) -> str:
    paragraphs = raw.split("\n\n")
    cleaned_paragraphs: list[str] = []

    for paragraph in paragraphs:
        lines = [" ".join(line.split()) for line in paragraph.splitlines() if len(line.split()) >= 3]
        if lines:
            cleaned_paragraphs.append("\n".join(lines))

    return "\n\n".join(cleaned_paragraphs)


def chunk_text(text: str, max_chunks: int, max_chars_per_chunk: int = 3000) -> list[str]:
    paragraphs = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        separator = "\n\n" if current else ""
        candidate = f"{current}{separator}{paragraph}"
        if len(candidate) <= max_chars_per_chunk:
            current = candidate
            continue

        if current:
            chunks.append(current)
            if len(chunks) >= max_chunks:
                return chunks

        if len(paragraph) <= max_chars_per_chunk:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            end = min(start + max_chars_per_chunk, len(paragraph))
            chunks.append(paragraph[start:end].strip())
            if len(chunks) >= max_chunks:
                return chunks
            start = end
        current = ""

    if current and len(chunks) < max_chunks:
        chunks.append(current)

    return chunks[:max_chunks]
