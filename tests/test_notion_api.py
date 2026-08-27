#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for notion_api.py conversion helpers (no network required)."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "notion"))

import notion_api  # noqa: E402


class RichTextTest(unittest.TestCase):
    def test_plain(self):
        rt = notion_api.rich_text("hello world")
        self.assertEqual(len(rt), 1)
        self.assertEqual(rt[0]["text"]["content"], "hello world")
        self.assertNotIn("annotations", rt[0])

    def test_bold(self):
        rt = notion_api.rich_text("a **b** c")
        parts = [r["text"]["content"] for r in rt]
        self.assertEqual("".join(parts), "a b c")
        bold = [r for r in rt if r.get("annotations", {}).get("bold")]
        self.assertEqual(len(bold), 1)
        self.assertEqual(bold[0]["text"]["content"], "b")

    def test_italic_and_code_and_link(self):
        rt = notion_api.rich_text("`code` *em* [t](https://x.io)")
        contents = [r["text"]["content"] for r in rt]
        self.assertEqual("".join(contents), "code em t")
        code = [r for r in rt if r.get("annotations", {}).get("code")]
        self.assertEqual(code[0]["text"]["content"], "code")
        link = [r for r in rt if r["text"].get("link")]
        self.assertEqual(link[0]["text"]["link"]["url"], "https://x.io")

    def test_empty(self):
        rt = notion_api.rich_text("")
        self.assertEqual(rt[0]["text"]["content"], "")


class MarkdownToBlocksTest(unittest.TestCase):
    def test_headings_and_paragraph(self):
        blocks = notion_api.markdown_to_blocks("# H1\n\n## H2\n\n正文")
        types = [b["type"] for b in blocks]
        self.assertEqual(types, ["heading_1", "heading_2", "paragraph"])
        self.assertEqual(blocks[0]["heading_1"]["rich_text"][0]["text"]["content"], "H1")
        self.assertEqual(blocks[2]["paragraph"]["rich_text"][0]["text"]["content"], "正文")

    def test_lists_and_todo(self):
        blocks = notion_api.markdown_to_blocks("- item1\n1. item2\n- [x] done\n- [ ] todo")
        types = [b["type"] for b in blocks]
        self.assertEqual(types, ["bulleted_list_item", "numbered_list_item", "to_do", "to_do"])
        self.assertEqual(blocks[1]["numbered_list_item"]["rich_text"][0]["text"]["content"], "item2")
        self.assertTrue(blocks[2]["to_do"]["checked"])
        self.assertFalse(blocks[3]["to_do"]["checked"])

    def test_code_fence(self):
        blocks = notion_api.markdown_to_blocks("```\nprint(1)\n```")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["type"], "code")
        self.assertEqual(blocks[0]["code"]["rich_text"][0]["text"]["content"], "print(1)")

    def test_quote_and_divider(self):
        blocks = notion_api.markdown_to_blocks("> cite\n---")
        types = [b["type"] for b in blocks]
        self.assertEqual(types, ["quote", "divider"])


class BlockToMdTest(unittest.TestCase):
    def test_basic_roundtrip(self):
        cases = [
            ({"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "T"}]}}, "# T"),
            ({"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "P"}]}}, "P"),
            ({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "B"}]}}, "- B"),
            ({"type": "to_do", "to_do": {"rich_text": [{"plain_text": "D"}], "checked": True}}, "- [x] D"),
        ]
        for block, expected in cases:
            self.assertEqual(notion_api.block_to_md(block), expected)


class PageTitleTest(unittest.TestCase):
    def test_title(self):
        page = {"properties": {"Name": {"type": "title", "title": [{"plain_text": "任务"}]}}}
        self.assertEqual(notion_api.page_title(page), "任务")

    def test_untitled(self):
        self.assertEqual(notion_api.page_title({"properties": {}}), "(无标题)")


if __name__ == "__main__":
    unittest.main()
