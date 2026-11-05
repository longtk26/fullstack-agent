"""Python source helpers shared by backend codegen and the plugins (Stories 17.6, 10.1)."""

import sys


class Imports:
    """`import x` / `from a import b` lines in isort order: stdlib, third party, first party (src)."""

    def __init__(self) -> None:
        self.modules: set[str] = set()
        self.names: dict[str, set[str]] = {}

    def add(self, module: str, *names: str) -> "Imports":
        if names:
            self.names.setdefault(module, set()).update(names)
        else:
            self.modules.add(module)
        return self

    def render(self) -> str:
        groups: list[list[str]] = [[], [], []]
        for module in self.modules:
            groups[self._group(module)].append((f"import {module}", module))
        for module, names in self.names.items():
            ordered = sorted(names, key=lambda name: (not name.isupper() or len(name) == 1, name.lower(), name))
            line = f"from {module} import {', '.join(ordered)}"
            if len(line) > 120:
                line = f"from {module} import (\n" + "".join(f"    {name},\n" for name in ordered) + ")"
            groups[self._group(module)].append((line, module))
        blocks = []
        for group in groups:
            lines = [line for line, _ in sorted(group, key=lambda item: (item[0].startswith("from "), item[1]))]
            if lines:
                blocks.append("\n".join(lines))
        return "\n\n".join(blocks) + "\n" if blocks else ""

    @staticmethod
    def _group(module: str) -> int:
        root = module.split()[0].split(".")[0]
        if root in sys.stdlib_module_names:
            return 0
        return 2 if root in ("src", "tests") or module.startswith(".") else 1
