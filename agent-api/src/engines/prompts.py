import hashlib
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel

from .port import PromptRef

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PURPOSES = ("draft_spec", "generate_database", "generate_backend", "generate_tests", "repair_code")


class RenderedPrompt(BaseModel):
    ref: PromptRef
    text: str


def untrusted(value: Any, name: str = "data") -> str:
    """Wraps spec text, requirements, validation output… so the engine treats it as data, not instructions."""
    text = str(value).replace("</untrusted-data", "<\\/untrusted-data")
    return f'<untrusted-data name="{name}">\n{text}\n</untrusted-data>'


class PromptLibrary:
    def __init__(self, root: Path = PROMPTS_DIR):
        self.root = root
        self.env = Environment(
            loader=FileSystemLoader(root),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,
        )
        self.env.filters["untrusted"] = untrusted

    def render(self, purpose: str, version: str = "v1", **context: Any) -> RenderedPrompt:
        name = f"{purpose}/{version}.md"
        source = (self.root / name).read_text()
        ref = PromptRef(id=purpose, version=version, sha256=hashlib.sha256(source.encode()).hexdigest())
        return RenderedPrompt(ref=ref, text=self.env.get_template(name).render(**context))

    def conventions(self) -> str:
        return (self.root / "conventions.md").read_text()

    def frontend_conventions(self) -> str:
        return (self.root / "frontend_conventions.md").read_text()
