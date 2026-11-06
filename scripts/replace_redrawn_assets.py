#!/usr/bin/env python3
"""Safely replace verified textbook JPG references with redrawn SVG assets.

The original JPGs are never removed. Each sample is handled independently:
one failed verification produces a skip record and does not block other samples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "outputs/教材高清图与难度校准-20261021"
SAMPLES = REVIEW / "10张重绘小样清单.json"
INVENTORY = REVIEW / "708张图片定位与分类.json"
OUTPUT_ROOT = ROOT / "outputs/五册教材教参整合"
REPORT = REVIEW / "redraw-replacement-report.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def section_dir(section_id: str) -> Path:
    book = section_id.split("-", 1)[0]
    return OUTPUT_ROOT / book / section_id


def svg_is_valid(path: Path) -> tuple[bool, str]:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return False, f"SVG 无法解析: {exc}"
    if not root.tag.endswith("svg"):
        return False, "根元素不是 svg"
    ns = "{http://www.w3.org/2000/svg}"
    if root.findall(f".//{ns}image"):
        return False, "包含嵌入位图 image"
    geometry = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text"}
    if not any(node.tag.rsplit("}", 1)[-1] in geometry for node in root.iter()):
        return False, "没有可见 SVG 几何内容"
    return True, "ok"


def zip_with_student_update(zip_path: Path, old_ref: str, new_ref: str, svg_path: Path) -> bool:
    """Replace the student HTML reference and add SVG only when actually used."""
    with zipfile.ZipFile(zip_path, "r") as source:
        entries = {name: source.read(name) for name in source.namelist()}
    html = entries.get("student.html", b"").decode("utf-8")
    changed_html = old_ref in html
    if changed_html:
        html = html.replace(old_ref, new_ref)
        entries["student.html"] = html.encode("utf-8")
    used = new_ref in html
    if used:
        entries[new_ref] = svg_path.read_bytes()
    if not changed_html and not used:
        return False
    temp = zip_path.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as target:
        for name, payload in entries.items():
            target.writestr(name, payload)
    temp.replace(zip_path)
    return changed_html or used


def verify_sample(sample: dict, inventory: dict[str, dict]) -> dict:
    section_id = sample["section_id"]
    out = section_dir(section_id)
    svg_path = REVIEW / sample["svg"]
    original_path = ROOT / sample["original_path"]
    result = {
        "section_id": section_id,
        "figure": sample.get("figure"),
        "original_path": sample["original_path"],
        "svg": sample["svg"],
        "status": "skip",
        "reason": None,
    }
    if not out.is_dir():
        result["reason"] = f"章节输出目录不存在: {out.relative_to(ROOT)}"
        return result
    if not original_path.is_file():
        result["reason"] = f"原图不存在: {original_path.relative_to(ROOT)}"
        return result
    if not svg_path.is_file():
        result["reason"] = f"SVG 不存在: {svg_path.relative_to(ROOT)}"
        return result
    valid, reason = svg_is_valid(svg_path)
    if not valid:
        result["reason"] = reason
        return result
    actual_original_sha = sha256(original_path)
    inventory_item = inventory.get(sample["original_path"])
    if not inventory_item:
        result["reason"] = "708 张图片登记中找不到原图定位"
        return result
    if actual_original_sha != inventory_item.get("sha256"):
        result["reason"] = "原图与 708 张图片登记哈希不一致"
        return result
    metadata_path = out / "metadata.json"
    build_path = out / "build.json"
    if not metadata_path.is_file() or not build_path.is_file():
        result["reason"] = "章节 metadata.json/build.json 不完整"
        return result
    metadata = load(metadata_path)
    build = load(build_path)
    metadata_matches = [(ref, item) for ref, item in metadata.get("assets", {}).items()
                        if item.get("source") == sample["original_path"]]
    build_matches = [(ref, item) for ref, item in build.get("assets", {}).items()
                     if item.get("source") == sample["original_path"]]
    if len(metadata_matches) != 1 or len(build_matches) != 1:
        result["reason"] = f"章节资源来源匹配不唯一: metadata={len(metadata_matches)}, build={len(build_matches)}"
        return result
    old_ref, metadata_asset = metadata_matches[0]
    build_ref, build_asset = build_matches[0]
    if old_ref != build_ref or metadata_asset.get("sha256") != actual_original_sha or build_asset.get("sha256") != actual_original_sha:
        result["reason"] = "章节登记中的原图引用或哈希与实际原图不一致"
        return result
    if not old_ref.endswith(".jpg") or old_ref.startswith("/") or ".." in Path(old_ref).parts:
        result["reason"] = f"原图引用格式不安全: {old_ref}"
        return result
    prefix = old_ref.rsplit("/", 1)[-1].split("-", 1)[0] + "-"
    if prefix not in ("book-", "private-"):
        result["reason"] = f"无法识别资源前缀: {old_ref}"
        return result
    expected_private = prefix == "private-"
    if bool(metadata_asset.get("private")) != expected_private or bool(build_asset.get("private")) != expected_private:
        result["reason"] = "book/private 前缀与 private 标记不一致"
        return result
    new_ref = old_ref[:-4] + ".svg"
    target = out / new_ref
    result.update({"old_ref": old_ref, "new_ref": new_ref, "original_sha256": actual_original_sha,
                   "svg_sha256": sha256(svg_path), "private": expected_private})
    if target.exists() and sha256(target) != sha256(svg_path):
        result["reason"] = f"目标 SVG 已存在但内容不同: {target.relative_to(ROOT)}"
        return result
    files = [out / "teacher.html", out / "student.html", out / "content.json"]
    if any(not path.is_file() for path in files):
        result["reason"] = "章节缺少 teacher/student/content 文件"
        return result
    counts = {path.name: path.read_text(encoding="utf-8").count(old_ref) for path in files}
    if sum(counts.values()) == 0:
        result["reason"] = "原图引用未出现在章节实际文件中"
        return result
    if expected_private and counts["student.html"]:
        result["reason"] = "private 资源出现在学生页，拒绝扩大其分发范围"
        return result
    result["reference_counts"] = counts
    result["status"] = "replace"
    result["reason"] = "all checks passed"
    return result


def apply_one(result: dict) -> None:
    section_id = result["section_id"]
    out = section_dir(section_id)
    old_ref, new_ref = result["old_ref"], result["new_ref"]
    svg_source = REVIEW / result["svg"]
    target = out / new_ref
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(svg_source.read_bytes())
    for name in ("teacher.html", "student.html", "content.json"):
        path = out / name
        text = path.read_text(encoding="utf-8").replace(old_ref, new_ref)
        if name == "content.json":
            json.loads(text)
        path.write_text(text, encoding="utf-8")
    for name in ("metadata.json", "build.json"):
        path = out / name
        data = load(path)
        assets = data.get("assets", {})
        old = assets.pop(old_ref)
        assets[new_ref] = {
            "source": old["source"],
            "sha256": result["svg_sha256"],
            "private": bool(old.get("private")),
            "format": "svg",
            "redrawn_from": old_ref,
            "original_sha256": result["original_sha256"],
        }
        data["assets"] = assets
        data.setdefault("redrawn_assets", []).append({
            "ref": new_ref, "from": old_ref, "source": old["source"],
            "original_sha256": result["original_sha256"], "svg_sha256": result["svg_sha256"],
        })
        # Build artifact hashes cover the files whose bytes changed; metadata/build are not self-hashed.
        for artifact in ("teacher.html", "student.html", "content.json"):
            data.setdefault("artifact_hashes", {})[artifact] = sha256(out / artifact)
        zip_path = out / "student.zip"
        if zip_path.is_file():
            zip_with_student_update(zip_path, old_ref, new_ref, target)
            data.setdefault("artifact_hashes", {})["student.zip"] = sha256(zip_path)
        save(path, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply verified replacements; default is dry-run")
    args = parser.parse_args()
    samples = load(SAMPLES)
    inventory = {item["original_path"]: item for item in load(INVENTORY)["items"]}
    results = [verify_sample(sample, inventory) for sample in samples]
    if args.apply:
        for result in results:
            if result["status"] == "replace":
                try:
                    apply_one(result)
                    result["applied"] = True
                except Exception as exc:  # keep the batch moving and retain a precise reason
                    result["status"] = "skip"
                    result["applied"] = False
                    result["reason"] = f"应用失败: {exc}"
            else:
                result["applied"] = False
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "apply" if args.apply else "dry-run",
        "replace_count": sum(r["status"] == "replace" for r in results),
        "skip_count": sum(r["status"] == "skip" for r in results),
        "results": results,
    }
    save(REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(r["status"] == "replace" for r in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
