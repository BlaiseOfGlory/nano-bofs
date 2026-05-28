from __future__ import annotations

import json
from typing import Any


def render_payload(payload: dict[str, Any], format_name: str) -> str:
    if format_name == "json":
        return json.dumps(payload.get("data", {}), indent=2)
    if format_name == "toon":
        return _render_toon(payload)
    return _render_text(payload)


def render_error(
    message: str,
    *,
    format_name: str,
    code: int,
    usage: str | None = None,
    help_items: list[str] | None = None,
) -> str:
    clean_message = message.strip()
    clean_usage = usage.strip() if usage else None
    clean_help = [item.strip() for item in (help_items or []) if item.strip()]

    data: dict[str, Any] = {
        "error": clean_message,
        "exit_code": code,
    }
    if clean_usage:
        data["usage"] = clean_usage
    if clean_help:
        data["help"] = clean_help

    sections: list[dict[str, Any]] = []
    if clean_usage:
        sections.append(
            {
                "type": "text",
                "name": "usage",
                "value": clean_usage,
            }
        )
    sections.append(
        {
            "type": "fields",
            "fields": {
                "error": clean_message,
                "exit_code": code,
            },
        }
    )
    if clean_help:
        sections.append(
            {
                "type": "messages",
                "name": "help",
                "items": clean_help,
            }
        )

    text_lines: list[str] = []
    if clean_usage:
        text_lines.extend(clean_usage.splitlines())
    if clean_message:
        prefix = "error: " if not clean_message.lower().startswith("error:") else ""
        text_lines.append(f"{prefix}{clean_message}")
    for item in clean_help:
        text_lines.append(f"help: {item}")

    return render_payload(
        {
            "data": data,
            "sections": sections,
            "text_lines": text_lines,
        },
        format_name,
    )


def _render_text(payload: dict[str, Any]) -> str:
    text_lines = payload.get("text_lines")
    if isinstance(text_lines, list):
        return "\n".join(str(line) for line in text_lines if str(line) != "").rstrip()
    return _render_text_from_sections(payload.get("sections", []))


def _render_text_from_sections(sections: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for section in sections:
        section_type = section.get("type")
        if section_type == "fields":
            name = str(section.get("name", "")).strip()
            fields = section.get("fields", {})
            if not isinstance(fields, dict):
                continue
            if name:
                lines.append(f"{name}:")
                for key, value in fields.items():
                    lines.append(f"  {key}: {value}")
            else:
                for key, value in fields.items():
                    lines.append(f"{key}: {value}")
        elif section_type == "table":
            name = str(section.get("name", "")).strip()
            fields = [str(item) for item in section.get("fields", [])]
            rows = section.get("rows", [])
            if name:
                lines.append(f"{name}:")
            if isinstance(rows, list):
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    values = ", ".join(f"{field}={row.get(field, '')}" for field in fields)
                    lines.append(f"- {values}")
            empty = str(section.get("empty", "")).strip()
            if empty and not rows:
                lines.append(empty)
        elif section_type == "messages":
            name = str(section.get("name", "")).strip()
            items = section.get("items", [])
            if name:
                lines.append(f"{name}:")
            if isinstance(items, list):
                for item in items:
                    lines.append(f"- {item}")
        elif section_type == "text":
            name = str(section.get("name", "")).strip()
            value = str(section.get("value", "")).rstrip()
            if name:
                lines.append(f"{name}:")
            lines.extend(value.splitlines())
    return "\n".join(lines).rstrip()


def _render_toon(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in payload.get("sections", []):
        section_type = section.get("type")
        if section_type == "fields":
            name = str(section.get("name", "")).strip()
            fields = section.get("fields", {})
            if not isinstance(fields, dict):
                continue
            if name:
                lines.append(f"{name}:")
                for key, value in fields.items():
                    lines.append(f"  {key}: {_toon_scalar(value)}")
            else:
                for key, value in fields.items():
                    lines.append(f"{key}: {_toon_scalar(value)}")
        elif section_type == "table":
            name = str(section.get("name", "")).strip()
            fields = [str(item) for item in section.get("fields", []) if str(item).strip()]
            rows = [row for row in section.get("rows", []) if isinstance(row, dict)]
            if rows:
                lines.append(f"{name}[{len(rows)}]{{{','.join(fields)}}}:")
                for row in rows:
                    lines.append(f"  {','.join(_toon_cell(row.get(field)) for field in fields)}")
            else:
                empty = str(section.get("empty", "")).strip()
                if empty:
                    lines.append(f"{name}: {empty}")
                else:
                    lines.append(f"{name}: 0 results")
        elif section_type == "messages":
            name = str(section.get("name", "")).strip()
            items = [str(item).strip() for item in section.get("items", []) if str(item).strip()]
            lines.append(f"{name}[{len(items)}]:")
            for item in items:
                lines.append(f"  {item}")
        elif section_type == "text":
            name = str(section.get("name", "")).strip()
            value = str(section.get("value", "")).rstrip()
            if name:
                lines.append(f"{name}:")
            for entry in value.splitlines():
                lines.append(f"  {entry}")
    return "\n".join(lines).rstrip()


def _toon_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _toon_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\r\n", "\n").replace("\n", "\\n")
    if not text or any(char in text for char in [",", "\""]) or text != text.strip():
        return json.dumps(text)
    return text
