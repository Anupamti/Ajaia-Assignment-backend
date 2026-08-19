import html

import bleach
import markdown as md

ALLOWED_TAGS = [
    "p", "br", "strong", "em", "u", "s",
    "h1", "h2", "h3", "ul", "ol", "li", "blockquote", "code", "pre",
]
ALLOWED_EXTENSIONS = {".txt", ".md"}


def is_supported_filename(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def file_to_html(filename: str, raw_bytes: bytes) -> str:
    text = raw_bytes.decode("utf-8", errors="replace")
    lower = filename.lower()

    if lower.endswith(".md"):
        rendered = md.markdown(text, extensions=["extra"])
    else:
        paragraphs = [f"<p>{html.escape(line)}</p>" for line in text.splitlines() if line.strip()]
        rendered = "\n".join(paragraphs) or "<p></p>"

    cleaned = bleach.clean(rendered, tags=ALLOWED_TAGS, attributes={}, strip=True)
    return cleaned or "<p></p>"
