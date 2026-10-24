# SPDX-License-Identifier: GPL-2.0-or-later
"""Static Qt Designer/handler inventory; no Qt or LinuxCNC imports or execution.

Model-Author: Codex. Run with --check to detect a stale committed inventory.
"""

import argparse
import ast
import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SCREEN = Path("screens/linumert")
OUTPUT = Path("docs/design/HMI_WIDGET_MAP.md")


def cell(value):
    return str(value).replace("|", "&#124;").replace("\n", " ")


def render(root=ROOT):
    ui_path = SCREEN / "linumert.ui"
    ui = ET.fromstring((root / ui_path).read_bytes())
    rows = ["# HMI-01 — mapa widgetów i połączeń", "",
            "Plik generowany: `python tools/hmi_inventory.py`. Nie edytować ręcznie.",
            "Pełny kontrakt i ograniczenia: [HMI_BASELINE.md](HMI_BASELINE.md).", ""]

    def table(title, headers, data):
        rows.extend([f"## {title}", "", "| " + " | ".join(headers) + " |",
                     "| " + " | ".join("---" for _ in headers) + " |"])
        rows.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in data)
        rows.append("")

    sources = [ui_path, SCREEN / "linumert_handler.py",
               SCREEN / "linumert_upstream_handler.py"]
    hashes = []
    for p in sources:
        data = (root / p).read_text(encoding="utf-8").encode("utf-8")
        hashes.append((p.as_posix(), hashlib.sha256(data).hexdigest()))
    table("Źródła", ["Plik", "SHA-256"], hashes)
    widgets = []
    stacks = []

    def visit(node, parent="—"):
        if node.tag == "widget":
            name = node.get("name")
            properties = []
            for prop in node.findall("property") + node.findall("attribute"):
                value = " ".join("".join(prop.itertext()).split())
                properties.append(f"{prop.get('name')}={value}")
            widgets.append((name, node.get("class"), parent, "; ".join(properties)))
            if node.get("class") in {"QStackedWidget", "QTabWidget"}:
                for i, page in enumerate(node.findall("widget")):
                    stacks.append((name, i, page.get("name")))
            parent = name
        for child in node:
            visit(child, parent)

    visit(ui)
    table(f"Widgety ({len(widgets)})", ["Nazwa", "Klasa", "Rodzic", "Właściwości UI"], widgets)
    table("Indeksy stron", ["Kontener", "Indeks", "Strona"], stacks)
    table("Połączenia Designer", ["Nadawca", "Sygnał", "Odbiorca", "Slot"],
          [[c.findtext(k, "") for k in ("sender", "signal", "receiver", "slot")]
           for c in ui.findall("./connections/connection")])
    table("Widgety niestandardowe", ["Klasa", "Baza", "Moduł"],
          [[c.findtext(k, "") for k in ("class", "extends", "header")]
           for c in ui.findall("./customwidgets/customwidget")])
    for path in sources[1:]:
        tree = ast.parse((root / path).read_text(encoding="utf-8"))
        references, calls = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and ast.unparse(node.value) == "self.w":
                references.append((node.lineno, node.attr, "atrybut"))
            elif isinstance(node, ast.Subscript) and ast.unparse(node.value) == "self.w":
                references.append((node.lineno, ast.unparse(node.slice), "indeks / dynamiczne"))
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if (name.endswith(".connect") or name.startswith("ACTION.")
                        or name == "KEYBIND.add_call"):
                    calls.append((node.lineno, ast.unparse(node)))
        table(f"{path.name}: zależności self.w", ["Linia", "Nazwa / wyrażenie", "Dostęp"],
              sorted(set(references)))
        table(f"{path.name}: sygnały i ACTION", ["Linia", "Wywołanie"], sorted(calls))
    return "\n".join(rows) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / OUTPUT
    result = render()
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != result:
            parser.exit(1, "Mapa HMI nieaktualna: uruchom python tools/hmi_inventory.py\n")
    else:
        target.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    main()
