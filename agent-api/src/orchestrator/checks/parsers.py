"""Turns tool output into structured failures {file, line, code, message} for digests and repair prompts."""

import json
import re
import xml.etree.ElementTree as ET
from typing import Any

TRACEBACK_FRAME = re.compile(r'File "/work/([^"]+)", line (\d+)')


def ruff_failures(output: str) -> list[dict[str, Any]]:
    start = output.find("[")
    try:
        items = json.loads(output[start:]) if start >= 0 else []
    except json.JSONDecodeError:
        return []
    return [
        {
            "file": item.get("filename", "").removeprefix("/work/"),
            "line": (item.get("location") or {}).get("row"),
            "code": item.get("code"),
            "message": item.get("message"),
        }
        for item in items
    ]


def junit_failures(xml_text: str, limit: int = 40) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    failures = []
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is None:
                continue
            text = (node.text or "") + "\n" + (node.get("message") or "")
            frames = TRACEBACK_FRAME.findall(text)
            path = (case.get("classname") or "").replace(".", "/")
            failures.append(
                {
                    "file": frames[-1][0] if frames else f"{path}.py",
                    "line": int(frames[-1][1]) if frames else None,
                    "test": case.get("name"),
                    "kind": kind,
                    "message": (node.get("message") or "")[:500],
                    "excerpt": text.strip()[-1500:],
                }
            )
    return failures[:limit]


def traceback_frames(output: str) -> list[dict[str, Any]]:
    return [{"file": file, "line": int(line)} for file, line in TRACEBACK_FRAME.findall(output)]


def last_lines(output: str, count: int = 40) -> str:
    return "\n".join(output.strip().splitlines()[-count:])
