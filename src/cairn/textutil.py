"""Small text helpers: slugs, YAML-safe quoting, a flat front-matter reader, hashing."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(s: str) -> str:
    """Lowercase, hyphenated, ASCII-only form of `s` (R15)."""
    decomposed = unicodedata.normalize("NFKD", s)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _NON_SLUG.sub("-", ascii_only.lower()).strip("-")


def yaml_str(s: str) -> str:
    """Quote `s` as a YAML double-quoted scalar. A JSON string is one (R5)."""
    return json.dumps(s, ensure_ascii=False)


def read_front_matter(text: str) -> dict[str, str]:
    """Return the top-level `key: value` scalars between the first two `---` lines (R6).

    Only reads flat scalars the tool wrote itself; nested values are returned as raw text.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if not line or line[0] in " \t#-":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        result[key.strip()] = _scalar(value.strip())
    return {}


def _scalar(value: str) -> str:
    if value[:1] in ('"', "'"):
        quote = value[0]
        end = value.find(quote, 1)
        while end > 0 and (
            (quote == '"' and value[end - 1] == "\\")
            or (quote == "'" and value[end + 1 : end + 2] == "'")
        ):
            end = value.find(quote, end + 2 if quote == "'" else end + 1)
        if end > 0:
            inner = value[: end + 1]
            if quote == '"':
                try:
                    return json.loads(inner)
                except ValueError:
                    return inner[1:-1]
            return inner[1:-1].replace("''", "'")
    hash_at = value.find(" #")
    if hash_at >= 0:
        value = value[:hash_at]
    elif value.startswith("#"):
        value = ""
    return value.strip()


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()
