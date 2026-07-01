"""Python Execution Tool — Safe sandboxed Python code execution."""

from __future__ import annotations

import ast
import io
import sys
from typing import Any

from .base import BaseTool

# ── Allowed imports ───────────────────────────────────────────────────────

ALLOWED_IMPORTS = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot",
    "json", "math", "statistics", "datetime", "collections",
    "itertools", "functools", "typing", "dataclasses", "copy",
    "decimal", "fractions", "random", "re", "string", "textwrap",
    "pprint", "csv", "io", "operator",
}

# ── Forbidden calls ───────────────────────────────────────────────────────

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "open", "__import__", "globals",
    "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "input",
}

FORBIDDEN_ATTRS = {
    ("os", "system"),
    ("os", "popen"),
    ("os", "remove"),
    ("os", "unlink"),
    ("os", "rmdir"),
    ("os", "chmod"),
    ("subprocess", "run"),
    ("subprocess", "Popen"),
    ("subprocess", "call"),
    ("subprocess", "check_output"),
    ("shutil", "rmtree"),
    ("shutil", "move"),
    ("shutil", "copy"),
    ("sys", "exit"),
    ("sys", "setrecursionlimit"),
}

FORBIDDEN_MODULES = {
    "os", "subprocess", "shutil", "sys", "ctypes", "socket",
    "requests", "urllib", "http", "ftplib", "telnetlib",
    "smtplib", "pickle", "shelve", "marshal", "code",
    "codeop", "pty", "fcntl", "posix", "pwd", "grp",
    "multiprocessing", "threading", "concurrent",
    "signal", "mmap", "gc", "traceback", "inspect",
    "importlib", "pkgutil", "pathlib", "tempfile",
}


class CodeSafetyChecker(ast.NodeVisitor):
    """AST visitor that checks Python code for dangerous operations."""

    def __init__(self) -> None:
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                self.violations.append(f"Forbidden import: {alias.name}")
            elif alias.name not in ALLOWED_IMPORTS and alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                self.violations.append(f"Disallowed import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        module_root = node.module.split(".")[0]
        if module_root in FORBIDDEN_MODULES:
            self.violations.append(f"Forbidden import from: {node.module}")
        elif module_root not in ALLOWED_IMPORTS and node.module not in ALLOWED_IMPORTS:
            self.violations.append(f"Disallowed import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check for direct forbidden function calls
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(f"Forbidden function call: {node.func.id}")
        elif isinstance(node.func, ast.Attribute):
            # Check for method calls like os.system
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                method_name = node.func.attr
                if (module_name, method_name) in FORBIDDEN_ATTRS:
                    self.violations.append(f"Forbidden method call: {module_name}.{method_name}")
                if method_name in FORBIDDEN_CALLS:
                    self.violations.append(f"Forbidden method call: {method_name}")
        self.generic_visit(node)


def check_python_code_safety(code: str) -> tuple[bool, str]:
    """Check if Python code is safe to execute.

    Args:
        code: Python source code string.

    Returns:
        Tuple of (is_safe: bool, reason: str)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in code: {e}"

    checker = CodeSafetyChecker()
    checker.visit(tree)

    if checker.violations:
        return False, "; ".join(checker.violations[:5])

    return True, "OK"


class PythonExecutionTool(BaseTool):
    """Execute Python code in a restricted sandbox environment.

    Performs AST-based safety checks before execution. Only allows
    a predefined set of safe imports. Blocks dangerous operations
    like file I/O, subprocess calls, and dynamic code execution.

    Captures stdout and returns it along with any results.
    """

    name: str = "python_execution"
    description: str = (
        "Python代码执行工具，在安全沙箱中执行数据分析或图表生成代码。"
        "内置AST安全检查，禁止危险操作。"
    )

    async def run(self, input: dict) -> dict:
        """Execute Python code safely.

        Args:
            input: dict with keys:
                - code (str): Python code to execute
                - globals_dict (dict, optional): Variables to inject into the runtime

        Returns:
            dict with success, stdout, result, and error
        """
        try:
            code = input.get("code", "")
            if not code:
                return {"success": False, "data": None, "error": "Code is required"}

            # Safety check
            is_safe, reason = check_python_code_safety(code)
            if not is_safe:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Code safety check failed: {reason}",
                }

            # Execute in sandbox
            result = self._execute_safe(code, input.get("globals_dict", {}))

            return {"success": True, "data": result, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _execute_safe(self, code: str, extra_globals: dict) -> dict:
        """Execute code in a restricted namespace and capture output."""
        # Restricted globals
        safe_globals: dict[str, Any] = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "any": any,
                "all": all,
                "isinstance": isinstance,
                "type": type,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "ZeroDivisionError": ZeroDivisionError,
            },
        }
        safe_globals.update(extra_globals)

        # Capture stdout
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured

        local_vars: dict[str, Any] = {}
        try:
            exec(code, safe_globals, local_vars)
            stdout_content = captured.getvalue()
        finally:
            sys.stdout = old_stdout

        # Filter out builtins and private vars from local_vars
        result_vars = {
            k: str(v)[:500] if not isinstance(v, (int, float, bool, str, list, dict)) else v
            for k, v in local_vars.items()
            if not k.startswith("_")
        }

        return {
            "stdout": stdout_content,
            "variables": result_vars,
            "var_count": len(result_vars),
        }
