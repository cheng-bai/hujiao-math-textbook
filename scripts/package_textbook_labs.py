#!/usr/bin/env python3
"""Seal selected textbook experiments with Anatomy 1.1, without overwriting releases.

Example:
  python3 scripts/package_textbook_labs.py --results outputs/.../results.json

Optional browser receipt fields in results.json::

  {"assetValidation": {"slug": {
    "htmlSha256": "...", "checkedAt": "2026-10-20T01:00:00Z",
    "interaction": "pass", "offline": "pass",
    "sceneRestore": true, "stateRestore": true
  }}}

Optional --visual-reviews JSON contains an "assets" mapping. Each manually read
asset requires htmlSha256, previewSha256, checkedAt, reviewer, and screenshots
(paths relative to that JSON). Images and receipts become package evidence.
Missing or stale receipts remain pending, never inferred from screenshot existence.
"""

from __future__ import annotations

from project_paths import use_project_root, launch_browser
use_project_root()

import argparse
import hashlib
import json
import mimetypes
import re
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ("foundations", "space-sequence", "calculus-stats",
            "deep-geometry", "deep-analysis", "deep-spatial")
UUID_NAMESPACE = uuid.NAMESPACE_URL


class PackageError(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise PackageError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load(path):
    need(path.is_file() and not path.is_symlink(), f"Missing or symlink input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def checked_time(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


class Dependencies(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ("src", "poster", "data", "srcset"):
            if values.get(key):
                self.references.append(values[key])
        if tag == "link" and values.get("href"):
            self.references.append(values["href"])


def check_self_contained(document, preview):
    parser = Dependencies()
    parser.feed(document)
    references = parser.references + re.findall(r"url\(\s*['\"]?([^)'\"]+)", document + preview)
    for ref in references:
        need(ref.startswith(("data:", "#")), f"Entry is not self-contained; reference: {ref}")
    need(not re.search(r"(?:fetch\s*\(|XMLHttpRequest|importScripts\s*\(|@import\b)", document),
         "Network-capable dependency requires explicit offline review")
    for marker in ("/Users/", "C:\\", "127.0.0.1", "localhost"):
        need(marker not in document and marker not in preview, f"Private path/service in runtime: {marker}")
    tree = ET.fromstring(preview)
    for element in tree.iter():
        for attr, value in element.attrib.items():
            if attr.rsplit("}", 1)[-1] == "href":
                need(value.startswith(("data:", "#")), "SVG preview has external dependency")
    # Manifest 1.1 must not claim a state contract if only scene switching exists.
    need("hashchange" in document and re.search(r"\.get\(['\"]state['\"]\)", document),
         "Manifest 1.1 needs actual hash-json-v1 state restoration in the built HTML")


def split_state(spec):
    groups = {"math": {}, "view": {}, "lesson": {}}
    contracts = {"math": {}, "view": {}, "lesson": {}}
    parameters = {}
    for control in spec["controls"]:
        key = control["key"]
        declared = spec.get("stateKeys")
        if declared:
            matches = [group for group, keys in declared.items() if key in keys]
            need(len(matches) == 1 and matches[0] in groups, f"State key not uniquely grouped: {key}")
            group = matches[0]
        else:
            group = "view" if key == "yaw" else "lesson" if key in ("progress", "stage") else "math"
        value = spec["initial"][key]
        groups[group][key] = value
        typ = "boolean" if isinstance(value, bool) else "integer" if type(value) is int else "number" if isinstance(value, float) else "string"
        contract = {"type": typ}
        parameter = {"type": "enum" if control["type"] == "select" else typ, "default": value}
        if control["type"] == "select":
            options = [option["value"] for option in control["options"]]
            need(value in options, f"Invalid initial enum: {key}")
            if all(type(option) in (int, float) for option in options):
                contract["type"] = "number" if any(isinstance(option, float) for option in options) else "integer"
            contract["enum"] = options
            parameter["domain"] = "允许的离散选项：" + json.dumps(options, ensure_ascii=False)
        elif control["type"] == "range":
            low, high = control["min"], control["max"]
            need(low <= value <= high, f"Initial parameter outside display range: {key}")
            # A floating slider may have an integer initial value: its contract is still numeric.
            if control.get("step", 1) % 1 or low % 1 or high % 1:
                contract["type"] = parameter["type"] = "number"
            contract.update(minimum=low, maximum=high)
            parameter.update(display_range=[low, high], domain=f"本实验允许输入范围 [{low}, {high}]；不等同数学对象的一般定义域。")
        else:
            need(control["type"] == "checkbox", f"Unsupported control type: {control}")
            parameter["domain"] = "布尔状态：显示/隐藏；不改变数学条件。"
        contracts[group][key] = contract
        if group == "math":
            parameters[key] = parameter
    need(set(spec["initial"]) == {c["key"] for c in spec["controls"]}, "Initial/control state mismatch")
    declared = spec.get("stateKeys")
    if declared:
        expected = {group: sorted(values) for group, values in groups.items()}
        if set(declared) == set(expected):
            need({k: sorted(v) for k, v in declared.items()} == expected, "LAB_SPEC stateKeys grouping differs")
        else:
            need(declared == {k: g for g, values in groups.items() for k in values}, "LAB_SPEC stateKeys grouping differs")
    return groups, contracts, parameters


def run(command, cwd=ROOT):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    need(result.returncode == 0, "Command failed: " + " ".join(map(str, command)) + "\n" + result.stdout + result.stderr)
    return result


def file_record(relative, payload, role):
    item = {"path": relative, "role": role, "sha256": sha(payload), "bytes": len(payload)}
    mime = mimetypes.guess_type(relative)[0]
    if mime:
        item["media_type"] = mime
    return item


def pick_version(output, asset_id, conflict):
    base = output / asset_id
    need(not base.is_symlink(), f"Release parent must not be a symlink: {base}")
    version = "1.0.0"
    if not (base / version).exists():
        return version
    need(conflict == "bump-patch", f"Immutable release already exists: {base / version}; use --on-conflict bump-patch")
    patch = 1
    while (base / f"1.0.{patch}").exists():
        patch += 1
    return f"1.0.{patch}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, required=True, help="Actual unified browser results.json")
    parser.add_argument("--selection", type=Path, default=ROOT / "docs/textbook-visual-selection.json")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/教材可视化资源库")
    parser.add_argument("--db", type=Path, help="Project-local SQLite; default OUTPUT/library.sqlite")
    parser.add_argument("--anatomy-tool", type=Path, default=ROOT / "tools/anatomy/scripts/resources.py")
    parser.add_argument("--visual-reviews", type=Path, help="Explicit manual screenshot-reading receipts; otherwise visual=pending")
    parser.add_argument("--on-conflict", choices=("error", "bump-patch"), default="error")
    parser.add_argument("--dry-run", action="store_true", help="Read/preflight only, do not run tests or create packages")
    parser.add_argument("--families", nargs="+", choices=FAMILIES,
                        help="Seal only these families; preserve every existing immutable release")
    args = parser.parse_args()
    output = args.output.resolve()
    db = (args.db or output / "library.sqlite").resolve()
    need(output.is_relative_to((ROOT / "outputs").resolve()), "Output must stay in this project's outputs directory")
    need(db.parent == output and db.suffix in (".sqlite", ".sqlite3", ".db"), "SQLite must be directly inside the project resource output, outside releases")
    need(args.anatomy_tool.is_file(), "Anatomy resources.py is unavailable")
    audit = load(args.selection.resolve())
    need(audit.get("assetCount") == len(audit["assets"]), "Audit asset count mismatch")
    need(len({a["id"] for a in audit["assets"]}) == len(audit["assets"]), "Duplicate experiment ids")
    results = load(args.results.resolve())
    visual_data = load(args.visual_reviews.resolve()) if args.visual_reviews else {"assets": {}}
    family_assets = {}
    family_inputs = {}
    families = tuple(args.families or FAMILIES)
    for family in families:
        config_path = ROOT / f"scripts/textbook-labs/{family}.json"
        config = load(config_path)
        sources = [ROOT / f"scripts/textbook-labs/{name}" for name in
                   (f"{family}.js", f"{family}.json", f"test-{family}.mjs", "lab-core.js", "lab-runtime.js", "lab.css")]
        review = ROOT / f"docs/review-{family}.md"
        need(review.is_file(), f"Missing independent review: {review}")
        for source in sources:
            need(source.is_file() and not source.is_symlink(), f"Missing family source: {source}")
        family_inputs[family] = (sources, review)
        for item in config["assets"]:
            need(item["id"] not in family_assets, "Duplicate family module")
            family_assets[item["id"]] = (family, item)

    plans = []
    for asset in audit["assets"]:
        slug = asset["id"]
        if slug not in family_assets and args.families:
            continue
        need(re.fullmatch(r"[a-z][a-z0-9-]{0,79}", slug), f"Unsafe asset slug: {slug}")
        identity = asset["resourceId"]
        need(str(uuid.UUID(identity)) == identity, f"Invalid permanent UUID: {slug}")
        need(identity == str(uuid.uuid5(UUID_NAMESPACE, "hujiao-textbook:" + slug)), "Audit resource identity changed")
        family, spec = family_assets[slug]
        html_path = ROOT / f"scripts/visual-assets/textbook-{slug}.html"
        preview_path = ROOT / f"scripts/visual-assets/textbook-{slug}-preview.svg"
        for source in (html_path, preview_path):
            need(source.is_file() and not source.is_symlink(), f"Missing generated asset: {source}")
        document, preview = html_path.read_text(encoding='utf-8'), preview_path.read_text(encoding='utf-8')
        need(sha(html_path.read_bytes()) == asset["hash"], f"Generated HTML differs from audit: {slug}")
        match = re.search(r"window\.LAB_SPEC=(.*?);</script>", document, re.S)
        need(match, f"Missing embedded LAB_SPEC: {slug}")
        embedded = json.loads(match.group(1))
        for key in ("id", "title", "goal", "summary", "formula", "initial", "controls"):
            need(embedded[key] == spec[key], f"Embedded/current source mismatch: {slug}/{key}")
        if spec.get("stateKeys"):
            need(embedded.get("stateKeys") == spec["stateKeys"], f"Stale state grouping: {slug}")
        if spec.get("explanationHtml"):
            need(spec["explanationHtml"] in document, f"Stale mathematical explanation: {slug}; rebuild first")
        for source in family_inputs[family][0]:
            if source.suffix in (".js", ".css"):
                need(source.read_text(encoding='utf-8') in document, f"HTML embeds stale source: {slug}/{source.name}")
        check_self_contained(document, preview)
        groups, contract, parameters = split_state(embedded)
        plans.append({"asset": asset, "family": family, "spec": spec, "html": html_path,
                      "preview": preview_path, "state": groups, "contract": contract,
                      "parameters": parameters, "version": pick_version(output, slug, args.on_conflict)})
    need(plans and len(plans) == len(family_assets), "Requested family/audit coverage mismatch")
    need(len({plan["asset"]["resourceId"] for plan in plans}) == len(plans), "Permanent UUID collision")
    if args.dry_run:
        print(json.dumps({"status": "preflight-only", "assets": len(plans), "output": str(output),
                          "versions": {p["asset"]["id"]: p["version"] for p in plans}}, ensure_ascii=False, indent=2))
        return

    model_receipts = {}
    for family in families:
        script = f"scripts/textbook-labs/test-{family}.mjs"
        executed = run(["node", script])
        sources = family_inputs[family][0]
        model_receipts[family] = {"family": family, "command": ["node", script],
                                  "execution_context": "原教材项目根目录。测试还核对教材落点；资源包不包含整册教材，运行同一测试需原项目。",
                                  "checked_at": utcnow(), "returncode": 0,
                                  "stdout": executed.stdout, "stderr": executed.stderr,
                                  "tested_files": [{"path": "source/" + p.name, "sha256": sha(p.read_bytes())}
                                                   for p in sources if p.name not in ("lab-runtime.js", "lab.css")]}
    output.parent.mkdir(parents=True, exist_ok=True)
    published = []
    with tempfile.TemporaryDirectory(prefix=".textbook-resource-stage-", dir=output.parent) as temporary:
        stage = Path(temporary)
        for plan in plans:
            asset, family, spec = plan["asset"], plan["family"], plan["spec"]
            slug, version = asset["id"], plan["version"]
            package = stage / slug / version
            package.mkdir(parents=True)
            payloads = {}

            def put(relative, payload, role):
                need(relative not in payloads, "Duplicate package payload: " + relative)
                target = package / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                payloads[relative] = file_record(relative, payload, role)

            put("index.html", plan["html"].read_bytes(), "runtime")
            put("previews/preview.svg", plan["preview"].read_bytes(), "runtime")
            for source in family_inputs[family][0]:
                put("source/" + source.name, source.read_bytes(), "source")
            put("source/asset.json", encode(spec), "source")
            put("evidence/independent-review.md", family_inputs[family][1].read_bytes(), "evidence")
            put("evidence/model-tests.json", encode(model_receipts[family]), "evidence")
            checks = [line for line in results.get("checksDetail", []) if slug in str(line) or any(sid in str(line) for sid in asset.get("sections", []))]
            receipt = results.get("assetValidation", {}).get(slug, {})
            browser_excerpt = {"status": results.get("status"), "errors": results.get("errors", []),
                               "asset": slug, "checksDetail": checks, "assetValidation": receipt,
                               "originalResultsSha256": sha(args.results.read_bytes())}
            put("evidence/browser-results.json", encode(browser_excerpt), "evidence")
            put("evidence/offline-static.json", encode({"checked_at": utcnow(), "status": "pass",
                "scope": "静态检查：HTML与SVG无外部依赖/私有绝对路径；内嵌源码与当前受检源码相同。不是浏览器离线验收。",
                "runtimeSha256": payloads["index.html"]["sha256"]}), "evidence")
            put("LICENSE.txt", ("Private local teaching resource. No public redistribution license is granted.\n"
                "Generated module authorship and review are AI-assisted; original textbook, reference, and third-party rights remain with their respective holders.\n").encode(), "license")
            put("README.md", (f"# {asset['title']}\n\n打开 index.html#scene=explore。使用相对文件离线运行，不需要本机端口。\n\n"
                "原生MathML公式；数值和采样图不能代替证明。完整状态契约见 manifest.json。\n"
                "validation 的四类状态分别解释；pending 不代表通过。源码和独立检查证据已随包携带。\n"
                "纯模型可复用，入口可独立离线运行；源测试含原项目教材落点检查，复跑完整测试需要原项目，不宣称包内携带整册教材。\n").encode(), "document")
            timestamp = utcnow()
            runtime_tested = [{"path": "index.html", "sha256": payloads["index.html"]["sha256"]}]
            same_runtime = receipt.get("htmlSha256") == runtime_tested[0]["sha256"] and checked_time(receipt.get("checkedAt"))
            global_browser_passed = results.get("status") == "passed" and not results.get("errors")
            validation = [{"kind": "mathematics", "status": "pass", "checked_at": model_receipts[family]["checked_at"],
                           "scope": "当前纯模型的自动独立关系与边界测试通过；随附独立数学复核，不以动态取样代替全域证明。",
                           "evidence": ["evidence/model-tests.json", "evidence/independent-review.md"],
                           "tested_files": model_receipts[family]["tested_files"]}]
            for kind in ("interaction", "offline"):
                passed = same_runtime and global_browser_passed and receipt.get(kind) == "pass"
                if kind == "interaction":
                    passed = passed and receipt.get("sceneRestore") is True and receipt.get("stateRestore") is True
                check = {"kind": kind, "status": "pass" if passed else "pending",
                         "scope": ("同一HTML哈希的真实浏览器检查；交互须含场景和hash-json状态恢复。" if kind == "interaction"
                                   else "同一HTML哈希的浏览器file离线检查；静态依赖检查单独附证。"),
                         "evidence": ["evidence/browser-results.json"] + (["evidence/offline-static.json"] if kind == "offline" else [])}
                if passed:
                    check.update(checked_at=receipt["checkedAt"], tested_files=runtime_tested)
                validation.append(check)
            visual = visual_data.get("assets", {}).get(slug, {})
            visual_passed = (visual.get("htmlSha256") == payloads["index.html"]["sha256"]
                             and visual.get("previewSha256") == payloads["previews/preview.svg"]["sha256"]
                             and checked_time(visual.get("checkedAt")) and bool(visual.get("reviewer"))
                             and bool(visual.get("screenshots")))
            images = []
            if visual_passed:
                for i, name in enumerate(visual["screenshots"]):
                    source = (args.visual_reviews.resolve().parent / name).resolve()
                    need(source.is_file() and source.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"), "Missing visual evidence: " + name)
                    relative = f"evidence/visual-{i}{source.suffix.lower()}"
                    put(relative, source.read_bytes(), "evidence")
                    images.append(relative)
                put("evidence/visual-review.json", encode({k: v for k, v in visual.items() if k != "screenshots"}), "evidence")
            visual_record = {"kind": "visual", "status": "pass" if visual_passed else "pending",
                             "scope": "明确逐资产人工读图记录覆盖的截图；截图存在本身不等于视觉已检查。",
                             "evidence": images + (["evidence/visual-review.json"] if visual_passed else [])}
            if visual_passed:
                visual_record.update(checked_at=visual["checkedAt"], tested_files=runtime_tested +
                                     [{"path": "previews/preview.svg", "sha256": payloads["previews/preview.svg"]["sha256"]}])
            validation.append(visual_record)
            metadata = {"schema_version": "1.1", "asset_id": asset["resourceId"], "version": version,
                        "slug": slug, "title": asset["title"], "language": "zh-CN", "created_at": timestamp,
                        "updated_at": timestamp, "contributors": [{"name": f"Codex {family} implementation", "role": "author"},
                            {"name": "Codex independent mathematical review", "role": "reviewer"}],
                        "rights": {"license": "LicenseRef-Private-Project-Use-No-Public-Grant",
                                   "attribution": "本地教师教材整合项目的AI辅助模块；原教材、教参与第三方素材权利归原权利人。"},
                        "math": {"topics": ["高中数学", family], "audience": ["高中数学教师", "学生探索"],
                                 "objects": [asset["title"]], "conditions": [asset["summary"]],
                                 "learning_goals": [asset["goal"]], "parameters": plan["parameters"],
                                 "approximation": "曲线采样和数值指标为近似演示；具体限制见入口提示与纯模型复核。三维屏幕投影不表示真实长度角度。"},
                        "entrypoints": {"html": "index.html", "svg": "previews/preview.svg"},
                        "files": list(payloads.values()), "scenes": [{"id": "explore", "title": "初始探索", "state": plan["state"]}],
                        "state_contract": plan["contract"], "default_state": plan["state"], "state_link": "hash-json-v1",
                        "provenance": {"sources": [{"title": "五册沪教教材与教参整合的教材专用实验", "note": json.dumps(asset["sourceReuse"], ensure_ascii=False) if isinstance(asset.get("sourceReuse"), (dict, list)) else asset.get("sourceReuse") or asset["goal"]}], "relations": []},
                        "validation": validation,
                        "extensions": {"textbook": {"sections": asset.get("sections", []), "placements": asset["placements"]},
                                       "source_build_sha256": asset["hash"], "family": family}}
            metadata_path = stage / f"{slug}.metadata.json"
            metadata_path.write_bytes(encode(metadata))
            run([sys.executable, str(args.anatomy_tool), "seal", str(package), "--metadata", str(metadata_path)])
            run([sys.executable, str(args.anatomy_tool), "validate", str(package)])

        # Validate every staged release before publishing any. Never overwrite sealed directories.
        for plan in plans:
            target = output / plan["asset"]["id"] / plan["version"]
            need(not target.exists() and not target.is_symlink() and not target.parent.is_symlink(),
                 "Concurrent release or symlink appeared; refusing overwrite: " + str(target))
        for plan in plans:
            slug, version = plan["asset"]["id"], plan["version"]
            target = output / slug / version
            target.parent.mkdir(parents=True, exist_ok=True)
            (stage / slug / version).rename(target)
            published.append(target)
        # Anatomy index imports the complete batch in one transaction. On index failure,
        # retain the valid immutable packages for explicit recovery; do not delete artifacts.
        try:
            run([sys.executable, str(args.anatomy_tool), "index", *map(str, published), "--db", str(db)])
        except PackageError as error:
            raise PackageError(str(error) + "\nSealed packages remain intact; only index registration needs recovery.") from error
    print(json.dumps({"status": "sealed-and-indexed", "assets": len(published), "database": str(db),
                      "packages": [str(p) for p in published]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (PackageError, ValueError, OSError, KeyError) as error:
        print("Packaging refused: " + str(error), file=sys.stderr)
        sys.exit(1)
