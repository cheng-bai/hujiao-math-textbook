"""Conservatively attach example-specific teacher-book notes to example analyses."""
from __future__ import annotations

import copy
import re
from collections import defaultdict

_BLANK = re.compile(r"\n[ \t]*\n+")
_HEADING = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")
_SECTION_ID = re.compile(r"-(\d+)-(\d+)(?:-|$)")
_SECTION_NUMBER = re.compile(r"(?<!\d)(\d{1,2})\s*\.\s*(\d{1,2})(?!\d)")
_EXAMPLE = re.compile(r"例(?:题)?\s*[·]?\s*(\d{1,3})")
_MATH_BLOCK = re.compile(r"\$\$[\s\S]*?\$\$")


def _paragraphs(text: str):
    """Return paragraph spans while keeping blank-line delimiters out of spans."""
    protected = [(m.start(), m.end()) for m in _MATH_BLOCK.finditer(text)]
    spans = []
    cursor = 0
    for sep in _BLANK.finditer(text):
        if any(start <= sep.start() < end for start, end in protected):
            continue
        raw = text[cursor:sep.start()]
        if raw.strip():
            left = cursor + len(raw) - len(raw.lstrip())
            right = cursor + len(raw.rstrip())
            spans.append((left, right, text[left:right]))
        cursor = sep.end()
    raw = text[cursor:]
    if raw.strip():
        left = cursor + len(raw) - len(raw.lstrip())
        right = cursor + len(raw.rstrip())
        spans.append((left, right, text[left:right]))
    return spans


def _example_number(title: str):
    match = _EXAMPLE.search(title or "")
    return int(match.group(1)) if match else None


def _referenced_examples(paragraph: str):
    """Read only the opening example list; later cross-references are not targets."""
    text = paragraph.replace("．", ".").lstrip()
    refs = set()
    match = _EXAMPLE.match(text)
    if not match:
        return refs
    number = int(match.group(1))
    refs.add(number)
    cursor = match.end()
    while cursor < len(text):
        tail = text[cursor:]
        range_match = re.match(r"\s*(?:至|到|[-—–~～])\s*例?\s*(\d{1,3})", tail)
        if range_match:
            end = int(range_match.group(1))
            if number < end <= number + 30:
                refs.update(range(number, end + 1))
            cursor += range_match.end()
            break
        list_match = re.match(r"\s*(?:、|和|与|及|或)\s*例?\s*(\d{1,3})", tail)
        if list_match:
            number = int(list_match.group(1))
            refs.add(number)
            cursor += list_match.end()
            continue
        break
    return refs


def _current_section(blocks):
    for block in blocks:
        if block.get("type") != "question":
            continue
        match = _SECTION_ID.search(block.get("id", ""))
        if match:
            return f"{int(match.group(1))}.{int(match.group(2))}"
    return None


def _heading_section(text: str):
    # Source headings sometimes wrap the number in TeX; stripping TeX markers is safe here.
    plain = text.replace("$", "").replace("{", "").replace("}", "")
    match = _SECTION_NUMBER.search(plain)
    return f"{int(match.group(1))}.{int(match.group(2))}" if match else None


def prepare_example_guidance(blocks):
    """Copy blocks and attach clearly referenced teacher notes to same-section examples.

    The output is intended for rendering after source images have been remapped. Original
    source blocks and provenance are retained in the returned blocks; moved notes are
    additionally recorded in per-question ``teacher_guidance_sources`` metadata.
    """
    result = copy.deepcopy(blocks)
    report = {
        "schema_version": 1,
        "policy": "explicit-example-reference-and-same-section-only",
        "source_groups": 0,
        "source_paragraphs": 0,
        "matched_source_groups": 0,
        "moved_source_paragraphs": 0,
        "attached_paragraphs": 0,
        "reused_existing_paragraphs": 0,
        "attachments": [],
        "unmatched": [],
    }
    current_section = _current_section(result)
    examples = defaultdict(list)
    for block in result:
        if block.get("type") == "question" and block.get("category") == "例题":
            number = _example_number(block.get("title", ""))
            if number is not None:
                examples[number].append(block)

    for source in result:
        if source.get("type") != "teacher" or not source.get("markdown"):
            continue
        # Only the pedagogical analysis block is a source of example-specific guidance.
        if "分析" not in source.get("title", ""):
            continue
        text = source["markdown"]
        spans = _paragraphs(text)
        if not spans:
            continue
        headings = list(_HEADING.finditer(text))
        scheduled = []
        pending = None
        context_section = None

        def flush_pending():
            nonlocal pending
            if pending:
                scheduled.append(pending)
                pending = None

        for start, end, paragraph in spans:
            while headings and headings[0].start() < start:
                heading = headings.pop(0)
                declared = _heading_section(heading.group(1))
                if declared:
                    flush_pending()
                    context_section = declared

            refs = _referenced_examples(paragraph)
            is_heading = paragraph.startswith("#")
            if is_heading:
                flush_pending()
                continue
            if refs:
                flush_pending()
                # A single paragraph that opens a precise procedure owns its contiguous
                # explanation/formula/list until another example or a heading begins.
                pending = {"refs": refs, "paragraphs": [(start, end, paragraph)],
                           "section": context_section, "continued": paragraph.rstrip().endswith((":", "："))}
                continue
            continuation = re.match(r"^(?:[（(]?\d+[)）.、]|第[一二三四五六七八九十]+步|首先|其次|然后|最后|等式|为纠正这类错误)", paragraph)
            if pending:
                back_reference = re.match(r"^(?:本例|本题|该例|该题|此例|此题|例题中|在本例|对于本例|这一例|这个例题|而[（(]\d|在推导过程中|验证这是|该方法|于是$|这个证明|对于无斜率情况|注意三点|这里得到的面积公式)", paragraph)
                earlier_example = re.match(r"^在例\s*(\d+)", paragraph)
                if earlier_example and int(earlier_example.group(1)) in pending["refs"]:
                    back_reference = True
                figure_or_formula = re.match(r"^(?:\$\$|!\[|图\s*\d)", paragraph)
                if (pending["continued"] and continuation) or back_reference or figure_or_formula:
                    pending["paragraphs"].append((start, end, paragraph))
                    pending["continued"] = bool(pending["continued"] and (continuation or figure_or_formula)) or paragraph.rstrip().endswith((":", "："))
                    continue
                pending["continued"] = False
                flush_pending()
        flush_pending()

        remove_spans = []
        for item in scheduled:
            report["source_groups"] += 1
            report["source_paragraphs"] += len(item["paragraphs"])
            section = item["section"]
            refs = item["refs"]
            reason = None
            if not current_section or not section:
                reason = "section-unconfirmed"
            elif section != current_section:
                reason = "section-mismatch"
            valid = [n for n in sorted(refs) if len(examples.get(n, [])) == 1]
            missing = sorted(refs - set(valid))
            if reason or missing:
                report["unmatched"].append({
                    "source_id": source.get("id"),
                    "provenance": copy.deepcopy(source.get("provenance", [])),
                    "examples_referenced": sorted(refs),
                    "section": section,
                    "reason": reason or "missing-or-ambiguous-example-block",
                    "unconfirmed_examples": missing,
                    "text": "\n\n".join(p[2] for p in item["paragraphs"]),
                })
                continue

            note = "\n\n".join(p[2] for p in item["paragraphs"])
            source_refs = copy.deepcopy(source.get("provenance", []))
            for number in valid:
                for question in examples[number]:
                    existing = question.get("teacher_analysis", "").strip()
                    missing_paragraphs = []
                    canonical_existing = re.sub(r"\s+", "", existing)
                    for _, _, paragraph in item["paragraphs"]:
                        if re.sub(r"\s+", "", paragraph) in canonical_existing:
                            report["reused_existing_paragraphs"] += 1
                        else:
                            missing_paragraphs.append(paragraph)
                    if missing_paragraphs:
                        addition = "### 教参原文提示\n\n" + "\n\n".join(missing_paragraphs)
                        question["teacher_analysis"] = (existing + "\n\n" + addition).strip() if existing else addition
                    report["attached_paragraphs"] += len(missing_paragraphs)
                    question.setdefault("analysis_provenance", [])
                    for ref in source_refs:
                        if ref not in question["analysis_provenance"]:
                            question["analysis_provenance"].append(copy.deepcopy(ref))
                    question.setdefault("teacher_guidance_sources", []).append({
                        "source_id": source.get("id"),
                        "provenance": copy.deepcopy(source_refs),
                        "examples_referenced": sorted(refs),
                        "section": section,
                        "provenance_precision": "source-block-line-range",
                    })
                    report["attachments"].append({
                        "question_id": question.get("id"),
                        "example_number": number,
                        "source_id": source.get("id"),
                        "provenance": copy.deepcopy(source_refs),
                    })
            report["matched_source_groups"] += 1
            report["moved_source_paragraphs"] += len(item["paragraphs"])
            remove_spans.extend((p[0], p[1]) for p in item["paragraphs"])

        if remove_spans:
            chunks = []
            cursor = 0
            for start, end in sorted(set(remove_spans)):
                chunks.append(text[cursor:start])
                cursor = end
            chunks.append(text[cursor:])
            residual = "".join(chunks)
            # Avoid leaving a string of empty paragraphs after extraction.
            residual = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", residual).strip()
            source["markdown"] = residual

    report["matched_examples"] = len({item["question_id"] for item in report["attachments"]})
    report["unmatched_groups"] = len(report["unmatched"])
    report["unmatched_paragraphs"] = report["source_paragraphs"] - report["moved_source_paragraphs"]
    report["attachment_count"] = len(report["attachments"])
    report["current_section"] = current_section
    return result, report
