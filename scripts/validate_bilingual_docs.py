#!/usr/bin/env python3
"""Validate structural parity and local links for the bilingual skill documentation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REFERENCE_NAMES = (
    "visual-styles.md",
    "imagegen-prompts.md",
    "project-schema.md",
    "tts-and-subtitles.md",
    "rendering-and-qa.md",
    "production-lessons.md",
)


def fail(message: str) -> None:
    raise ValueError(message)


def markdown_shape(text: str) -> tuple[int, int, int, int, int, int]:
    return (
        len(re.findall(r"(?m)^## ", text)),
        len(re.findall(r"(?m)^### ", text)),
        text.count("```"),
        len(re.findall(r"(?m)^\|", text)),
        len(re.findall(r"(?m)^- ", text)),
        len(re.findall(r"(?m)^\d+\. ", text)),
    )


def numbered_sections(text: str) -> list[str]:
    return re.findall(r"(?m)^## (\d+)\.", text)


def bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)\n```", text, re.S)


def resolve_markdown_links(path: Path) -> None:
    for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        if "://" in link or link.startswith("#"):
            continue
        relative = link.split("#", 1)[0]
        if relative and not (path.parent / relative).resolve().exists():
            fail(f"Broken local link in {path}: {link}")


def json_example(path: Path) -> Any:
    match = re.search(r"```json\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
    if not match:
        fail(f"Missing JSON example in {path}")
    return json.loads(match.group(1))


def type_tree(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: type_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [type_tree(item) for item in value]
    return type(value).__name__


def validate(root: Path) -> None:
    english_skill = root / "SKILL.md"
    chinese_skill = root / "SKILL.zh-CN.md"
    for path in (english_skill, chinese_skill):
        if not path.is_file():
            fail(f"Missing bilingual skill edition: {path}")

    english = english_skill.read_text(encoding="utf-8")
    chinese = chinese_skill.read_text(encoding="utf-8")
    if numbered_sections(english) != numbered_sections(chinese):
        fail("English and Chinese workflow section numbers differ")
    if markdown_shape(english) != markdown_shape(chinese):
        fail("English and Chinese heading, command, table, or rule-list structure differs")
    if bash_blocks(english) != bash_blocks(chinese):
        fail("English and Chinese Bash commands differ")
    if "references/zh-CN/" not in chinese:
        fail("Chinese edition must route references to references/zh-CN/")
    if "validate_bilingual_docs.py" not in english or "validate_bilingual_docs.py" not in chinese:
        fail("Both editions must require bilingual validation after rule changes")

    references = root / "references"
    for name in REFERENCE_NAMES:
        english_path = references / name
        chinese_path = references / "zh-CN" / name
        if not english_path.is_file() or not chinese_path.is_file():
            fail(f"Missing reference counterpart for {name}")
        if markdown_shape(english_path.read_text(encoding="utf-8")) != markdown_shape(
            chinese_path.read_text(encoding="utf-8")
        ):
            fail(f"Heading, code-fence, or table structure differs for {name}")

    if type_tree(json_example(references / "project-schema.md")) != type_tree(
        json_example(references / "zh-CN" / "project-schema.md")
    ):
        fail("English and Chinese project-schema examples differ structurally")

    for path in (english_skill, chinese_skill, *references.glob("*.md"), *(references / "zh-CN").glob("*.md")):
        resolve_markdown_links(path)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    try:
        validate(root)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Bilingual documentation validation failed: {exc}", file=sys.stderr)
        return 1
    print("Bilingual documentation validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
