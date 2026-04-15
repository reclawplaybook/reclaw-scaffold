"""
src/memory.py — Flat File Memory Read/Write

All agent memory lives in workspace/memory/ as plain Markdown files.
This module provides four operations:

  read_memory(filename)        — read a file, return content string
  write_memory(filename, text) — append text to a file (create if missing)
  search_memory(query)         — keyword search across all memory files
  list_memory()                — list all memory filenames

Design philosophy:
  - No database. No vectors. Just files you can read, edit, and grep.
  - The simplicity is intentional: you should be able to open any memory file
    in a text editor and understand it immediately.
  - To add vector search later, wrap search_memory() with an embedding lookup.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger("memory")

MEMORY_DIR = os.path.join(
    os.path.dirname(__file__), "..", "workspace", "memory"
)


def _ensure_dir():
    """Create the memory directory if it doesn't exist."""
    os.makedirs(MEMORY_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def read_memory(filename: str) -> str:
    """
    Read a file from workspace/memory/.

    Args:
        filename: e.g. "tasks.md" or "agent_log.md"

    Returns:
        File content as a string, or "" if the file doesn't exist.
    """
    _ensure_dir()
    path = os.path.join(MEMORY_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.debug(f"memory: '{filename}' not found")
        return ""
    except Exception:
        logger.exception(f"memory: error reading '{filename}'")
        return ""


def write_memory(filename: str, content: str, mode: str = "a") -> bool:
    """
    Write or append to a file in workspace/memory/.

    Args:
        filename: e.g. "tasks.md"
        content:  The text to write.
        mode:     'a' to append (default), 'w' to overwrite.

    Returns:
        True on success, False on failure.
    """
    _ensure_dir()
    path = os.path.join(MEMORY_DIR, filename)
    try:
        with open(path, mode, encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"memory: wrote to '{filename}' (mode={mode})")
        return True
    except Exception:
        logger.exception(f"memory: error writing '{filename}'")
        return False


def search_memory(query: str, top_k: int = 3) -> list[tuple[str, str]]:
    """
    Naive keyword search across all files in workspace/memory/.

    Splits the query into tokens and scores each line by how many tokens it
    contains. Returns the top-k (filename, snippet) pairs.

    Args:
        query:  The search string (space-separated keywords).
        top_k:  Maximum number of results to return.

    Returns:
        List of (filename, snippet) tuples, best matches first.
        Returns [] if no matches or memory dir is empty.
    """
    _ensure_dir()

    tokens = [t.lower() for t in query.split() if len(t) > 2]
    if not tokens:
        return []

    scored: list[tuple[float, str, str]] = []

    try:
        for filename in os.listdir(MEMORY_DIR):
            if not filename.endswith((".md", ".txt", ".log")):
                continue
            path = os.path.join(MEMORY_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                continue

            for line in lines:
                lower_line = line.lower()
                score = sum(1 for t in tokens if t in lower_line)
                if score > 0:
                    snippet = line.strip()[:120]
                    scored.append((score, filename, snippet))

    except FileNotFoundError:
        return []

    scored.sort(key=lambda x: x[0], reverse=True)

    # Deduplicate: one result per file (highest-scoring line)
    seen_files: set[str] = set()
    results: list[tuple[str, str]] = []
    for _, filename, snippet in scored:
        if filename not in seen_files:
            results.append((filename, snippet))
            seen_files.add(filename)
        if len(results) >= top_k:
            break

    return results


def list_memory() -> list[str]:
    """
    List all filenames in workspace/memory/.

    Returns:
        Sorted list of filenames (not full paths), or [] if empty.
    """
    _ensure_dir()
    try:
        return sorted(
            f for f in os.listdir(MEMORY_DIR)
            if os.path.isfile(os.path.join(MEMORY_DIR, f))
        )
    except Exception:
        logger.exception("memory: error listing files")
        return []


# ---------------------------------------------------------------------------
# Manual test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    write_memory("test.md", "# Test\n- [ ] Sample open task\n- [x] Done task\n")
    print("Content:", read_memory("test.md"))
    print("Search:", search_memory("sample task"))
    print("Files:", list_memory())
