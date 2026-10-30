"""Bounded, shape-aware text copy for MCP tool results.

The MCP JSON-RPC envelope carries the full payload twice: `structuredContent`
(the authoritative data) and `content[0].text` (what the model reads). Large
component summaries can exceed 10–20 KB, and a naive character slice produces
invalid JSON. This helper shrinks the text copy while keeping it valid JSON:
arrays keep their head and tail with drop metadata, long strings are cut inside
the value, and paging/status scalars are preserved verbatim.

`structuredContent` must always be built from the untouched payload.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

PROTECTED_STRING_KEYS = {
    "continue",
    "continue_token",
    "next",
    "next_token",
    "page",
    "page_size",
    "total",
    "returned",
    "has_next",
    "status",
    "error",
    "error_code",
    "is_error",
    "exit_code",
    "kind",
    "name",
    "namespace",
    "context_id",
    "truncated",
}

ARRAY_HEAD = 5
ARRAY_TAIL = 10
MIN_STRING_KEEP = 240
MARKER_RESERVE = 320
DEFAULT_MAX_CHARS = 16_000


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _collect(
    node: Any,
    parent: Any,
    key: Any,
    arrays: List[Tuple[Any, Any, list]],
    strings: List[Tuple[Any, Any, str]],
) -> None:
    if isinstance(node, list):
        arrays.append((parent, key, node))
        for index, item in enumerate(node):
            _collect(item, node, index, arrays, strings)
    elif isinstance(node, dict):
        for child_key, child in node.items():
            _collect(child, node, child_key, arrays, strings)
    elif isinstance(node, str) and len(node) > MIN_STRING_KEEP:
        strings.append((parent, key, node))


def _mark(parent: Any, dropped: int, total: int, hint: str) -> None:
    if not isinstance(parent, dict):
        return
    parent["_truncated"] = True
    parent["_dropped_items_count"] = dropped
    parent["_total_unfiltered"] = total
    parent.setdefault("_truncation_hint", hint)


def _trim_array(item: Tuple[Any, Any, list], hint: str) -> bool:
    parent, _key, value = item
    if len(value) <= 1:
        return False
    tail = max(1, min(ARRAY_TAIL, len(value) - 1))
    head = min(ARRAY_HEAD, len(value) - tail)
    kept = value[:head] + value[-tail:]
    dropped = len(value) - len(kept)
    if dropped <= 0:
        return False
    total = len(value)
    value[:] = kept
    _mark(parent, dropped, total, hint)
    return True


def _trim_string(item: Tuple[Any, Any, str], hint: str) -> bool:
    parent, key, value = item
    if isinstance(key, str) and key in PROTECTED_STRING_KEYS:
        return False
    head = int(len(value) * 0.6)
    tail = int(len(value) * 0.25)
    dropped = len(value) - head - tail
    parent[key] = f"{value[:head]}\n... [truncated {dropped} chars ...]\n{value[-tail:]}"
    if isinstance(parent, dict):
        parent.setdefault("_truncated", True)
        parent.setdefault("_truncation_hint", hint)
    return True


def _shrink(value: Any, target: int, hint: str) -> Any:
    text = _dump(value)
    rounds = 0
    while len(text) > target and rounds < 64:
        rounds += 1
        arrays: List[Tuple[Any, Any, list]] = []
        strings: List[Tuple[Any, Any, str]] = []
        _collect(value, {}, "", arrays, strings)

        arrays.sort(key=lambda item: len(_dump(item[2])), reverse=True)
        trimmed = False
        for item in arrays:
            if _trim_array(item, hint):
                trimmed = True
                break
        if trimmed:
            text = _dump(value)
            continue

        strings.sort(key=lambda item: len(item[2]), reverse=True)
        for item in strings:
            if _trim_string(item, hint):
                trimmed = True
                break
        if trimmed:
            text = _dump(value)
            continue

        # Last resort: halve the largest remaining array.
        remaining = [item for item in arrays if len(item[2]) > 1]
        if not remaining:
            break
        parent, _key, array = remaining[0]
        keep = max(1, len(array) // 2)
        total = len(array)
        array[:] = array[-keep:]
        _mark(parent, total - keep, total, hint)
        text = _dump(value)

    return value


def render_result_text(
    data: Any,
    max_chars: int = DEFAULT_MAX_CHARS,
    hint: str | None = None,
) -> str:
    """Return a valid-JSON text copy of ``data`` bounded to ``max_chars``.

    The input is normalized through JSON first, so non-serializable values are
    stringified by the same rule as the MCP envelope and the original object is
    never mutated.
    """
    text = _dump(data)
    if len(text) <= max_chars:
        return text

    normalized = json.loads(_dump(data))
    hint = hint or (
        "Narrow the arguments (name/namespace/selector/page_size/limit) and "
        "retry; the result was truncated."
    )
    shrunk = _shrink(normalized, max(1_000, max_chars - MARKER_RESERVE), hint)
    return _dump(shrunk)
