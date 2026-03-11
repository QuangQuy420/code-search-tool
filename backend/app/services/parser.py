"""Tree-sitter code parser service.

Extracts meaningful code chunks (functions, classes, methods) from source files
using tree-sitter grammars for Python, JavaScript, TypeScript, Java, Go, and Rust.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjs
import tree_sitter_python as tspy
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)

MAX_FILE_LINES = 50_000
MAX_CHUNKS_PER_FILE = 500

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "__pycache__", ".next",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    "vendor", "target",
}

SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2",
    ".pdf", ".doc", ".docx",
    ".exe", ".dll", ".so", ".dylib",
    ".lock", ".min.js", ".min.css",
    ".map", ".pyc", ".pyo",
}

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
}

# Node types to extract per language
FUNCTION_NODE_TYPES: dict[str, list[str]] = {
    "python": ["function_definition", "class_definition"],
    "javascript": ["function_declaration", "class_declaration", "arrow_function", "method_definition"],
    "typescript": ["function_declaration", "class_declaration", "arrow_function", "method_definition"],
    "tsx": ["function_declaration", "class_declaration", "arrow_function", "method_definition"],
    "java": ["method_declaration", "class_declaration", "constructor_declaration"],
    "go": ["function_declaration", "method_declaration"],
    "rust": ["function_item", "impl_item", "struct_item"],
}


@dataclass(frozen=True)
class CodeChunk:
    code: str
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    language: str
    chunk_type: str  # "function" | "class" | "method"


def _get_language(lang_name: str) -> Language:
    """Get the tree-sitter Language object for a given language name."""
    lang_map = {
        "python": tspy.language(),
        "javascript": tsjs.language(),
        "typescript": tsts.language_typescript(),
        "tsx": tsts.language_tsx(),
        "java": tsjava.language(),
        "go": tsgo.language(),
        "rust": tsrust.language(),
    }
    lang = lang_map.get(lang_name)
    if lang is None:
        raise ValueError(f"Unsupported language: {lang_name}")
    return Language(lang)


def detect_language(file_path: str) -> str | None:
    """Auto-detect language from file extension."""
    suffix = Path(file_path).suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(suffix)


def should_skip_file(file_path: str) -> bool:
    """Check if a file should be skipped."""
    p = Path(file_path)

    # Skip by directory
    for part in p.parts:
        if part in SKIP_DIRS:
            return True

    # Skip by extension
    if p.suffix.lower() in SKIP_EXTENSIONS:
        return True

    return False


def _get_node_name(node, source_bytes: bytes) -> str:
    """Extract the name from a tree-sitter node."""
    # Look for a 'name' or 'identifier' child
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier"):
            return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")

    # For arrow functions assigned to variables: const foo = () => ...
    if node.type == "arrow_function" and node.parent:
        parent = node.parent
        if parent.type == "variable_declarator":
            for child in parent.children:
                if child.type in ("identifier", "name"):
                    return source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="replace")

    return "<anonymous>"


def _classify_chunk(node, language: str) -> str:
    """Determine if a node is a function, class, or method."""
    node_type = node.type

    if "class" in node_type or node_type == "impl_item" or node_type == "struct_item":
        return "class"

    # Check if function is inside a class (making it a method)
    if language == "python" and node_type == "function_definition":
        parent = node.parent
        while parent:
            if parent.type == "class_definition":
                return "method"
            parent = parent.parent

    if node_type in ("method_definition", "method_declaration", "constructor_declaration"):
        return "method"

    return "function"


def parse_file(file_path: str, language: str | None = None) -> list[CodeChunk]:
    """Parse a source file and extract code chunks.

    Args:
        file_path: Path to the source file.
        language: Programming language. Auto-detected from extension if None.

    Returns:
        List of CodeChunk objects extracted from the file.
    """
    if should_skip_file(file_path):
        return []

    if language is None:
        language = detect_language(file_path)
    if language is None:
        return []

    try:
        source = Path(file_path).read_bytes()
    except (OSError, UnicodeDecodeError):
        logger.warning("Could not read file: %s", file_path)
        return []

    # Skip very large files
    line_count = source.count(b"\n") + 1
    if line_count > MAX_FILE_LINES:
        logger.warning("Skipping large file (%d lines): %s", line_count, file_path)
        return []

    try:
        ts_language = _get_language(language)
    except ValueError:
        return []

    parser = Parser(ts_language)
    tree = parser.parse(source)

    target_types = FUNCTION_NODE_TYPES.get(language, [])
    if not target_types:
        return []

    chunks: list[CodeChunk] = []

    def _walk(node):
        if len(chunks) >= MAX_CHUNKS_PER_FILE:
            return

        if node.type in target_types:
            code = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            name = _get_node_name(node, source)
            chunk_type = _classify_chunk(node, language)

            chunks.append(CodeChunk(
                code=code,
                file_path=file_path,
                function_name=name,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=language,
                chunk_type=chunk_type,
            ))

        for child in node.children:
            _walk(child)

    _walk(tree.root_node)
    return chunks
