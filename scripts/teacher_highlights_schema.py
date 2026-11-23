"""JSON contract for per-browser teacher highlights (import/export validation)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


SCHEMA_VERSION = 1


def storage_key(section_id: str) -> str:
    return f'hujiao-teacher-highlights-v{SCHEMA_VERSION}:{section_id}'


def export_document(section_id: str, annotations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        'version': SCHEMA_VERSION,
        'sectionId': section_id,
        'edition': 'teacher',
        'exportedAt': datetime.now().astimezone().replace(microsecond=0).isoformat(),
        'annotations': [sanitize_annotation(item) for item in annotations],
    }


def sanitize_annotation(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(item.get('id', '')),
        'blockId': str(item.get('blockId', '')),
        'quote': str(item.get('quote', '')),
        'note': str(item.get('note', ''))[:2000],
        'color': item.get('color', 'warm') if item.get('color') in {'warm', 'green', 'blue'} else 'warm',
        'createdAt': str(item.get('createdAt', '')),
    }


def validate_import(raw: str | bytes | dict[str, Any], section_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    try:
        data = raw if isinstance(raw, dict) else json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return [], ['文件不是有效的 JSON']
    if not isinstance(data, dict):
        return [], ['根对象必须是 JSON 对象']
    if data.get('version') != SCHEMA_VERSION:
        errors.append('版本不匹配')
    if data.get('sectionId') != section_id:
        errors.append('节 ID 不匹配')
    if data.get('edition') != 'teacher':
        errors.append('仅支持教师版批注')
    rows = data.get('annotations')
    if not isinstance(rows, list):
        return [], errors + ['annotations 必须是数组']
    items: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f'第 {index + 1} 条不是对象')
            continue
        quote = str(row.get('quote', '')).strip()
        block_id = str(row.get('blockId', '')).strip()
        if not quote or not block_id:
            errors.append(f'第 {index + 1} 条缺少 blockId 或 quote')
            continue
        items.append(sanitize_annotation(row))
    return items, errors
