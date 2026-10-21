import unittest
import json
import re
from pathlib import Path
from example_guidance import prepare_example_guidance


def question(number, section="x1-2-2"):
    return {"type": "question", "id": f"{section}-ex-{number}",
            "title": f"例题 {number}", "category": "例题", "markdown": "stem",
            "answer": "answer", "teacher_analysis": "", "analysis_provenance": []}


class GuidanceTests(unittest.TestCase):
    def test_exact_note_attaches_with_provenance_without_mutating_input(self):
        blocks = [
            {"type": "section", "id": "x1-2-2", "number": "2.2"},
            question(1),
            {"type": "teacher", "id": "guide", "title": "正式教参 · 教材分析与教学建议",
             "provenance": [{"source": "teacher", "start": 5, "end": 8}],
             "markdown": "#### 2.2 椭圆\n\n例 1 旨在说明定义。\n\n一般教学建议不移动。"},
        ]
        result, report = prepare_example_guidance(blocks)
        self.assertEqual(blocks[1]["teacher_analysis"], "")
        self.assertIn("例 1 旨在说明定义。", result[1]["teacher_analysis"])
        self.assertEqual(result[1]["analysis_provenance"], [{"source": "teacher", "start": 5, "end": 8}])
        self.assertEqual(result[2]["markdown"], "#### 2.2 椭圆\n\n一般教学建议不移动。")
        self.assertEqual(report["attached_paragraphs"], 1)

    def test_compact_multi_example_note_and_math_block(self):
        blocks = [question(1), question(2), {
            "type": "teacher", "title": "教参教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n例 1、例 2 的计算过程如下：\n\n$$\nx=1\n\n y=2\n$$\n\n注意条件。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertIn("$$\nx=1\n\n y=2\n$$", result[0]["teacher_analysis"])
        self.assertEqual(result[0]["teacher_analysis"], result[1]["teacher_analysis"])
        self.assertEqual(result[2]["markdown"], "#### 2.2 椭圆\n\n注意条件。")
        self.assertEqual(report["matched_examples"], 2)

    def test_wrong_section_is_kept_unmatched(self):
        blocks = [question(1), {"type": "teacher", "title": "教材分析", "provenance": [],
                                "markdown": "#### 8.3 列联表\n\n例 1 说明检验步骤。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertEqual(result[1]["markdown"], blocks[1]["markdown"])
        self.assertEqual(report["unmatched"][0]["reason"], "section-mismatch")
        self.assertEqual(result[0]["teacher_analysis"], "")

    def test_explicit_range_maps_only_existing_examples(self):
        blocks = [question(1), question(2), question(3), {
            "type": "teacher", "title": "教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n例 1 至例 3 分别说明不同做法。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertTrue(all("不同做法" in result[i]["teacher_analysis"] for i in (0, 1, 2)))
        self.assertEqual(report["source_paragraphs"], 1)
        self.assertEqual(report["attached_paragraphs"], 3)

    def test_cross_reference_later_in_sentence_does_not_attach_to_that_example(self):
        blocks = [question(1), question(2), {
            "type": "teacher", "title": "教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n例 1 是上一节例 2 的延续。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertIn("上一节例 2", result[0]["teacher_analysis"])
        self.assertEqual(result[1]["teacher_analysis"], "")
        self.assertEqual(report["attachment_count"], 1)

    def test_missing_member_of_multi_example_group_keeps_whole_source(self):
        blocks = [question(1), question(2), {
            "type": "teacher", "title": "教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n例 1、例 3 分别说明不同做法。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertEqual(result[1]["markdown"], blocks[1]["markdown"])
        self.assertEqual(result[0]["teacher_analysis"], "")
        self.assertEqual(report["unmatched"][0]["unconfirmed_examples"], [3])

    def test_two_procedural_steps_remain_together(self):
        blocks = [question(1), {
            "type": "teacher", "title": "教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n例 1 的解题分两步：\n\n第一步，建立关系。\n\n第二步，求出结果。\n\n一般建议保留原处。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertIn("第二步，求出结果。", result[0]["teacher_analysis"])
        self.assertEqual(result[1]["markdown"], "#### 2.2 椭圆\n\n一般建议保留原处。")

    def test_preexisting_note_dedup_and_second_run_is_idempotent(self):
        text = "例 1 旨在说明定义。"
        blocks = [question(1), {
            "type": "teacher", "title": "教材分析", "provenance": [],
            "markdown": "#### 2.2 椭圆\n\n" + text}]
        blocks[0]["teacher_analysis"] = text
        once, report = prepare_example_guidance(blocks)
        twice, second_report = prepare_example_guidance(once)
        self.assertEqual(once[0]["teacher_analysis"], text)
        self.assertEqual(twice[0]["teacher_analysis"], text)
        self.assertEqual(report["reused_existing_paragraphs"], 1)
        self.assertEqual(second_report["attachment_count"], 0)

    def test_actual_five_book_samples_and_provenance_ranges(self):
        root = Path(__file__).resolve().parents[1]
        sample_ids = ["bx1-3-1", "bx2-6-1", "bx3-11-2", "x1-3-2", "x2-8-2"]
        def canonical(text):
            text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"![\1](IMAGE)", text)
            return re.sub(r"\s+", "", text)
        for section_id in sample_ids:
            path = next((root / "batch/sections").glob(f"*/{section_id}.json"))
            data = json.loads(path.read_text(encoding="utf-8"))
            for index, block in enumerate(data["blocks"]):
                block.setdefault("id", f"{section_id}-b{index}")
            output, report = prepare_example_guidance(data["blocks"])
            teacher_text = (root / data["sources"]["teacher"]).read_text(encoding="utf-8")
            for block in data["blocks"]:
                if block["type"] != "teacher" or "分析" not in block.get("title", ""):
                    continue
                for ref in block["provenance"]:
                    if ref["source"] != "teacher":
                        continue
                    source_range = "\n".join(teacher_text.splitlines()[ref["start"] - 1:ref["end"]])
                    self.assertIn(canonical(block["markdown"]), canonical(source_range), section_id)
            if section_id == "bx2-6-1":
                q = next(x for x in output if x.get("id") == "bx2-6-1-ex-1")
                self.assertEqual(q["teacher_analysis"].count("例 1 旨在说明"), 1)
                self.assertGreater(report["reused_existing_paragraphs"], 0)
            if section_id == "bx3-11-2":
                q = next(x for x in output if x.get("id") == "bx3-11-2-ex-1")
                self.assertIn("图 11-R1", q["teacher_analysis"])
                self.assertIn("![", q["teacher_analysis"])
            if section_id == "x1-3-2":
                q = next(x for x in output if x.get("id") == "x1-3-2-ex-2")
                self.assertIn("本例是向量方法", q["teacher_analysis"])
            if section_id == "x2-8-2":
                self.assertTrue(any(x["reason"] == "section-mismatch" for x in report["unmatched"]))

    def test_official_101_nodes_idempotence_and_stem_answer_preservation(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "batch/manifests/catalog.json").read_text(encoding="utf-8"))
        paths = [s["path"] for book in catalog["books"] for chapter in book["chapters"] for s in chapter["sections"]]
        self.assertEqual(len(paths), 101)
        for relative in paths:
            data = json.loads((root / relative).read_text(encoding="utf-8"))
            blocks = data["blocks"]
            for index, block in enumerate(blocks):
                block.setdefault("id", f"{data['id']}-b{index}")
            original_json = json.dumps(blocks, ensure_ascii=False)
            once, report = prepare_example_guidance(blocks)
            twice, _ = prepare_example_guidance(once)
            self.assertEqual(once, twice, data["id"])
            self.assertEqual(original_json, json.dumps(blocks, ensure_ascii=False), data["id"])
            source_questions = {b["id"]: b for b in blocks if b["type"] == "question"}
            for block in once:
                if block["type"] == "question":
                    original = source_questions[block["id"]]
                    for field in ("markdown", "answer"):
                        self.assertEqual(block.get(field, ""), original.get(field, ""), f"{data['id']} {block['id']} {field}")
            self.assertEqual(report["source_groups"], report["matched_source_groups"] + report["unmatched_groups"])
            self.assertEqual(report["source_paragraphs"], report["moved_source_paragraphs"] + report["unmatched_paragraphs"])

    def test_unresolved_reference_stays_in_teacher_source(self):
        blocks = [question(1), {"type": "teacher", "title": "教材分析", "provenance": [],
                                "markdown": "#### 2.2 椭圆\n\n例 9 是跨章节的拓展。"}]
        result, report = prepare_example_guidance(blocks)
        self.assertIn("例 9", result[1]["markdown"])
        self.assertEqual(report["unmatched_paragraphs"], 1)


if __name__ == "__main__":
    unittest.main()
