"""Report Export Tool — Export research reports to Markdown and HTML."""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

from .base import BaseTool

# ── HTML template with professional styling ───────────────────────────────

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --primary: #1a3a5c;
            --accent: #2563eb;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                         "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.8;
            padding: 40px 0;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            padding: 60px 70px;
        }}
        h1 {{
            font-size: 28px;
            color: var(--primary);
            border-bottom: 3px solid var(--accent);
            padding-bottom: 16px;
            margin-bottom: 32px;
            text-align: center;
        }}
        h2 {{
            font-size: 22px;
            color: var(--primary);
            margin-top: 40px;
            margin-bottom: 16px;
            padding-left: 12px;
            border-left: 4px solid var(--accent);
        }}
        h3 {{
            font-size: 18px;
            color: #334155;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        p {{ margin-bottom: 14px; text-align: justify; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        th, td {{
            border: 1px solid var(--border);
            padding: 10px 14px;
            text-align: left;
        }}
        th {{
            background: #f1f5f9;
            font-weight: 600;
            color: var(--primary);
        }}
        tr:hover {{ background: #f8fafc; }}
        ul, ol {{ margin: 12px 0 12px 28px; }}
        li {{ margin-bottom: 6px; }}
        blockquote {{
            border-left: 4px solid #94a3b8;
            padding: 12px 20px;
            margin: 16px 0;
            background: #f8fafc;
            color: #475569;
            font-style: italic;
        }}
        code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
        }}
        pre {{
            background: #1e293b;
            color: #e2e8f0;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
        }}
        pre code {{ background: none; padding: 0; color: inherit; }}
        .meta {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 14px;
            margin-bottom: 32px;
        }}
        .source-list {{
            background: #f8fafc;
            border-radius: 8px;
            padding: 20px 24px;
            margin: 20px 0;
        }}
        .source-list li {{ font-size: 13px; color: var(--text-secondary); }}
        .score-card {{
            display: inline-block;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 12px 20px;
            margin: 8px;
            text-align: center;
        }}
        .score-value {{
            font-size: 24px;
            font-weight: 700;
            color: var(--accent);
        }}
        .score-label {{ font-size: 12px; color: var(--text-secondary); }}
        @media print {{
            body {{ background: white; }}
            .container {{ box-shadow: none; padding: 20px; }}
        }}
        @media (max-width: 768px) {{
            .container {{ padding: 24px 20px; margin: 0 12px; }}
            h1 {{ font-size: 22px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {body}
    </div>
</body>
</html>"""


class ReportExportTool(BaseTool):
    """Export research reports to Markdown and HTML formats.

    Supports exporting to .md files and converting Markdown to
    styled HTML suitable for sharing or printing.
    """

    name: str = "report_export"
    description: str = (
        "报告导出工具，支持导出 Markdown 和 HTML 格式的研究报告。"
        "HTML格式包含专业排版样式，适合分享和打印。"
    )

    def __init__(self, export_dir: str = "./data/exports") -> None:
        """Initialize with export directory.

        Args:
            export_dir: Directory where exported files will be saved.
        """
        self.export_dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    async def run(self, input: dict) -> dict:
        """Export a report.

        Args:
            input: dict with keys:
                - action (str): 'export_md', 'export_html', or 'export_both'
                - content (str): Markdown report content
                - filename (str): Base filename (without extension)
                - title (str, optional): Report title for HTML

        Returns:
            dict with success status and exported file paths
        """
        try:
            action = input.get("action", "export_both")
            content = input.get("content", "")
            filename = input.get("filename", f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            title = input.get("title", "研究报告")

            if not content:
                return {"success": False, "data": None, "error": "content is required"}

            paths: dict[str, str] = {}

            if action in ("export_md", "export_both"):
                md_path = self._export_markdown(content, filename)
                paths["md"] = md_path

            if action in ("export_html", "export_both"):
                html_path = self._export_html(content, filename, title)
                paths["html"] = html_path

            return {
                "success": True,
                "data": {
                    "files": paths,
                    "filename": filename,
                    "timestamp": datetime.now().isoformat(),
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _export_markdown(self, content: str, filename: str) -> str:
        """Export content as a .md file."""
        safe_name = re.sub(r'[<>:"/\\\\|?*]', '_', filename)
        filepath = os.path.join(self.export_dir, f"{safe_name}.md")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    def _export_html(self, content: str, filename: str, title: str) -> str:
        """Convert Markdown to HTML and export."""
        html_body = self._markdown_to_html(content)
        full_html = _HTML_TEMPLATE.format(title=title, body=html_body)

        safe_name = re.sub(r'[<>:"/\\\\|?*]', '_', filename)
        filepath = os.path.join(self.export_dir, f"{safe_name}.html")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_html)
        return filepath

    def _markdown_to_html(self, md: str) -> str:
        """Simple Markdown to HTML converter.

        Handles: headings, bold, italic, lists, tables, code blocks,
        blockquotes, links, images, and horizontal rules.
        """
        lines = md.split("\n")
        html_lines: list[str] = []
        in_code_block = False
        in_table = False
        in_ul = False
        in_ol = False
        code_lines: list[str] = []
        table_rows: list[str] = []

        i = 0
        while i < len(lines):
            line = lines[i]

            # Code block
            if line.strip().startswith("```"):
                if in_code_block:
                    code_html = "\n".join(code_lines)
                    html_lines.append(f"<pre><code>{self._escape_html(code_html)}</code></pre>")
                    code_lines = []
                    in_code_block = False
                else:
                    in_code_block = True
                i += 1
                continue

            if in_code_block:
                code_lines.append(line)
                i += 1
                continue

            # Table
            if "|" in line and line.strip().startswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                table_rows.append(line)
                # Check if next line is separator or not a table
                if i + 1 < len(lines) and "|" in lines[i + 1] and "---" in lines[i + 1]:
                    i += 1
                    continue
                elif i + 1 >= len(lines) or "|" not in lines[i + 1]:
                    # End of table
                    html_lines.append(self._render_table(table_rows))
                    in_table = False
                    table_rows = []
                i += 1
                continue

            # Close lists if not a list item
            stripped = line.strip()
            if in_ul and not stripped.startswith("- ") and not stripped.startswith("* "):
                html_lines.append("</ul>")
                in_ul = False
            if in_ol and not re.match(r'^\d+\. ', stripped):
                html_lines.append("</ol>")
                in_ol = False

            # Headings
            if stripped.startswith("#### "):
                html_lines.append(f"<h4>{self._inline_format(stripped[5:])}</h4>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3>{self._inline_format(stripped[4:])}</h3>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{self._inline_format(stripped[3:])}</h2>")
            elif stripped.startswith("# "):
                html_lines.append(f"<h1>{self._inline_format(stripped[2:])}</h1>")

            # Blockquote
            elif stripped.startswith("> "):
                html_lines.append(f"<blockquote>{self._inline_format(stripped[2:])}</blockquote>")

            # Horizontal rule
            elif stripped in ("---", "***", "___"):
                html_lines.append("<hr>")

            # Unordered list
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not in_ul:
                    html_lines.append("<ul>")
                    in_ul = True
                html_lines.append(f"<li>{self._inline_format(stripped[2:])}</li>")

            # Ordered list
            elif re.match(r'^\d+\. ', stripped):
                if not in_ol:
                    html_lines.append("<ol>")
                    in_ol = True
                content = re.sub(r'^\d+\. ', '', stripped)
                html_lines.append(f"<li>{self._inline_format(content)}</li>")

            # Empty line
            elif not stripped:
                html_lines.append("")

            # Regular paragraph
            else:
                html_lines.append(f"<p>{self._inline_format(stripped)}</p>")

            i += 1

        # Close any open blocks
        if in_ul:
            html_lines.append("</ul>")
        if in_ol:
            html_lines.append("</ol>")
        if in_table:
            html_lines.append(self._render_table(table_rows))

        return "\n".join(html_lines)

    def _render_table(self, rows: list[str]) -> str:
        """Render a markdown table to HTML."""
        if not rows:
            return ""

        def parse_row(row: str) -> list[str]:
            return [cell.strip() for cell in row.strip("|").split("|")]

        html = "<table>\n"

        # Header
        if rows:
            cells = parse_row(rows[0])
            html += "<thead>\n<tr>\n"
            for cell in cells:
                html += f"<th>{self._inline_format(cell)}</th>\n"
            html += "</tr>\n</thead>\n"

        # Body (skip separator line)
        body_rows = [r for r in rows[1:] if "---" not in r]
        if body_rows:
            html += "<tbody>\n"
            for row in body_rows:
                cells = parse_row(row)
                html += "<tr>\n"
                for cell in cells:
                    html += f"<td>{self._inline_format(cell)}</td>\n"
                html += "</tr>\n"
            html += "</tbody>\n"

        html += "</table>"
        return html

    @staticmethod
    def _inline_format(text: str) -> str:
        """Handle inline formatting: bold, italic, code, links, images."""
        # Images
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1" style="max-width:100%">', text)
        # Links
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        return text

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
