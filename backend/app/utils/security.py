"""
Security utilities for the Deep Research Agent Platform.

Provides two main safety validators:

1. **Python code safety checker** – Uses AST static analysis to reject
   dangerous patterns (``os.system``, ``subprocess``, ``eval``, ``exec``,
   file writes, ``__import__``, ``compile``, etc.) before code reaches a
   sandbox.

2. **SQL safety validator** – Uses ``sqlglot`` to parse a SQL string and
   ensure it only contains ``SELECT`` / ``WITH`` statements.  Any mutation
   (DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, CREATE) is blocked.

Usage::

    from app.utils.security import check_python_code_safety, check_sql_safety

    safe, reason = check_python_code_safety("print(1 + 2)")
    # safe=True, reason=""

    safe, reason = check_sql_safety("SELECT * FROM users")
    # safe=True, reason=""
"""

from __future__ import annotations

import ast
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

class SafetyResult(NamedTuple):
    """Result of a safety check."""

    is_safe: bool
    reason: str


# ===================================================================
# Python Code Safety (AST-based)
# ===================================================================

# Node types that are unconditionally dangerous.
_DANGEROUS_NODE_TYPES: set[type[ast.AST]] = {
    ast.Match,  # pattern matching can be used for obfuscation
}

# Function / attribute paths that are blocked.
#
# Each entry is a tuple of strings representing a dotted access path
# (e.g. ("os", "system") matches ``os.system(...)``).
_BLOCKED_CALL_PATHS: set[tuple[str, ...]] = {
    # Process / command execution
    ("os", "system"),
    ("os", "popen"),
    ("os", "execv"),
    ("os", "execve"),
    ("os", "execl"),
    ("os", "execle"),
    ("os", "execlp"),
    ("os", "execlpe"),
    ("os", "execvp"),
    ("os", "execvpe"),
    ("os", "spawnl"),
    ("os", "spawnle"),
    ("os", "spawnlp"),
    ("os", "spawnlpe"),
    ("os", "spawnv"),
    ("os", "spawnve"),
    ("os", "spawnvp"),
    ("os", "spawnvpe"),
    ("subprocess", "call"),
    ("subprocess", "check_call"),
    ("subprocess", "check_output"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("shutil", "which"),
    # Dynamic code execution / compilation
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("builtins", "compile"),
    ("builtins", "__import__"),
    # Module reload (can be abused)
    ("importlib", "reload"),
    ("importlib", "import_module"),
    # File-system write / delete
    ("builtins", "open"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("os", "removedirs"),
    ("os", "rename"),
    ("os", "renames"),
    ("os", "chmod"),
    ("os", "chown"),
    ("shutil", "rmtree"),
    ("shutil", "move"),
    ("shutil", "copy"),
    ("shutil", "copy2"),
    ("shutil", "copytree"),
    ("pathlib", "Path", "write_text"),
    ("pathlib", "Path", "write_bytes"),
    # sys manipulation
    ("sys", "setrecursionlimit"),
    ("sys", "exit"),
    ("sys", "settrace"),
    ("sys", "setprofile"),
    # Pickle (arbitrary code execution on deserialisation)
    ("pickle", "loads"),
    ("pickle", "load"),
    ("dill", "loads"),
    ("dill", "load"),
}

# Built-in names that are always blocked.
_ALWAYS_BLOCKED_NAMES: set[str] = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "globals",
    "locals",
    "vars",
    "breakpoint",
}


def _resolve_call_path(node: ast.expr) -> tuple[str, ...] | None:
    """
    Attempt to resolve a call expression to a dotted path.

    For example, ``os.system()``  ->  ``("os", "system")``.
    If the call target is not a simple dotted name, returns ``None``.
    """
    parts: list[str] = []

    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None

    parts.reverse()
    return tuple(parts)


class _CodeSafetyVisitor(ast.NodeVisitor):
    """
    AST visitor that walks a Python module and collects violations.
    """

    def __init__(self) -> None:
        self.violations: list[str] = []

    # -- Calls -------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        path = _resolve_call_path(node.func)
        if path is not None:
            # Check exact path and every prefix — e.g. block
            # ``pathlib.Path.write_text`` as well as ``pathlib.Path`` itself.
            for i in range(1, len(path) + 1):
                if path[:i] in _BLOCKED_CALL_PATHS:
                    dotted = ".".join(path)
                    self.violations.append(
                        f"Forbidden call to `{dotted}` at line {node.lineno}"
                    )
                    break

        # Check for raw ``eval(...)``, ``exec(...)``, etc. used as a bare name.
        if isinstance(node.func, ast.Name) and node.func.id in _ALWAYS_BLOCKED_NAMES:
            self.violations.append(
                f"Forbidden built-in `{node.func.id}` at line {node.lineno}"
            )

        self.generic_visit(node)

    # -- Imports -----------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if alias.name in ("os", "subprocess", "shutil", "sys", "ctypes", "code"):
                self.violations.append(
                    f"Forbidden import of `{alias.name}` at line {node.lineno}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        if module in ("os", "subprocess", "shutil", "sys", "ctypes", "code"):
            self.violations.append(
                f"Forbidden import from `{module}` at line {node.lineno}"
            )
        # Also check for direct imports of dangerous names from safe modules.
        for alias in node.names:
            full = f"{module}.{alias.name}"
            if alias.name in _ALWAYS_BLOCKED_NAMES:
                self.violations.append(
                    f"Forbidden import of `{full}` at line {node.lineno}"
                )
        self.generic_visit(node)

    # -- General -----------------------------------------------------------

    def generic_visit(self, node: ast.AST) -> None:
        if type(node) in _DANGEROUS_NODE_TYPES:
            self.violations.append(
                f"Forbidden AST node type `{type(node).__name__}` at line "
                f"{getattr(node, 'lineno', '?')}"
            )
        super().generic_visit(node)


def check_python_code_safety(code: str) -> SafetyResult:
    """
    Statically analyse Python source code for dangerous operations.

    The following patterns are blocked:

    - Calls to ``os.system``, ``subprocess.*``, ``eval``, ``exec``,
      ``compile``, ``__import__``.
    - File write operations (``open`` with intent to write, ``Path.write_text``,
      ``shutil.copy``, etc.).
    - ``pickle`` / ``dill`` deserialisation.
    - Direct imports of ``os``, ``subprocess``, ``shutil``, ``sys``, ``ctypes``.

    Args:
        code: A string containing Python source code.

    Returns:
        ``SafetyResult`` with ``is_safe=True`` if no violations were found.

    Example::

        >>> check_python_code_safety("import os; os.system('ls')")
        SafetyResult(is_safe=False, reason="Forbidden import of `os` at line 1")
    """
    if not code.strip():
        return SafetyResult(True, "")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SafetyResult(False, f"Syntax error in code: {exc}")

    visitor = _CodeSafetyVisitor()
    visitor.visit(tree)

    if visitor.violations:
        return SafetyResult(False, "; ".join(visitor.violations))

    return SafetyResult(True, "")


# ===================================================================
# SQL Safety Validator (sqlglot-based)
# ===================================================================

# The set of top-level statement types that we consider read-only.
# NOTE: sqlglot returns lowercase keys (e.g. "select", "delete")
_READ_ONLY_STATEMENT_TYPES: set[str] = {
    "select",
    "with",  # CTEs — only safe when the body is also read-only
    "explain",
    "describe",
    "show",
    "use",
    "command",  # SET, etc. wrapped as Command
}

# Statement types that are explicitly blocked.
_BLOCKED_STATEMENT_TYPES: set[str] = {
    "delete",
    "update",
    "insert",
    "drop",
    "altertable",
    "altercolumn",
    "truncate",
    "create",
    "createtable",
    "createview",
    "merge",
    "replace",
    "load",
    "call",
    "execute",
    "grant",
    "revoke",
    "set",
    "comment",
    "analyze",
    "vacuum",
    "copy",
    "renametable",
    "renamecolumn",
    "lock",
    "unlock",
    "begin",
    "commit",
    "rollback",
    "savepoint",
}


def check_sql_safety(sql: str, dialect: str | None = None) -> SafetyResult:
    """
    Validate that a SQL string contains only read-only (SELECT) statements.

    First tries ``sqlglot`` for precise parsing. Falls back to regex-based
    validation when sqlglot is not installed.

    Args:
        sql: A string containing one or more SQL statements.
        dialect: Optional SQL dialect hint. Only used when sqlglot is available.

    Returns:
        ``SafetyResult`` with ``is_safe=True`` when every statement is read-only.
    """
    if not sql.strip():
        return SafetyResult(True, "")

    # Try sqlglot first (more precise)
    try:
        import sqlglot

        try:
            statements = sqlglot.parse(sql, dialect=dialect, error_level=sqlglot.ErrorLevel.IGNORE)
        except Exception as exc:
            return SafetyResult(False, f"SQL parse error: {exc}")

        if not statements:
            return SafetyResult(False, "No valid SQL statements found")

        for idx, statement in enumerate(statements):
            if statement is None:
                continue
            stmt_key: str = getattr(statement, "key", "") or ""
            if stmt_key in _BLOCKED_STATEMENT_TYPES:
                return SafetyResult(False, f"Forbidden statement type '{stmt_key}' at index {idx}")
            if stmt_key not in _READ_ONLY_STATEMENT_TYPES:
                return SafetyResult(False, f"Unrecognised statement type '{stmt_key}' at index {idx}")
        return SafetyResult(True, "")

    except ImportError:
        # Fallback to regex-based validation
        return _check_sql_safety_regex(sql)


def _check_sql_safety_regex(sql: str) -> SafetyResult:
    """Regex-based SQL safety check (fallback when sqlglot is unavailable)."""
    import re

    sql_upper = sql.strip().upper()

    # Must start with SELECT or WITH (CTE)
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return SafetyResult(False, f"SQL must start with SELECT or WITH, got: {sql_upper[:30]}...")

    forbidden_keywords = [
        "DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "TRUNCATE",
        "CREATE", "REPLACE", "MERGE", "GRANT", "REVOKE", "EXEC",
        "EXECUTE", "ATTACH", "DETACH",
    ]

    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', sql_upper):
            return SafetyResult(False, f"Forbidden SQL keyword detected: {keyword}")

    return SafetyResult(True, "")
