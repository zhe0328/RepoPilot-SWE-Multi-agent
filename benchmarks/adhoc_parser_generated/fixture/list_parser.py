"""Parse comma-separated tokens from user input."""


def parse_items(text: str) -> list[str]:
    """Return trimmed non-empty items from comma-separated text.

    Empty input must return an empty list (do not raise).
    """
    if text == "":
        raise ValueError("empty input")  # BUG: callers expect [] for empty CSV
    return [part.strip() for part in text.split(",") if part.strip()]
