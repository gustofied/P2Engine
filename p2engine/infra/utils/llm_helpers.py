def estimate_tokens(text: str) -> int:
    # quick-n-dirty ≈ GPT-2 tokenizer
    return int(len(text.encode("utf-8")) / 3.7)


def summarise(text: str, limit_chars: int = 750) -> str:
    if len(text) <= limit_chars:
        return text
    head = text[: limit_chars // 2]
    tail = text[-limit_chars // 2 :]
    return f"[[snip {len(text) - limit_chars} chars]]\n{head}\n...\n{tail}"
