def normalize_query(text: str) -> str:
    return " ".join(text.lower().strip().split())