"""Biblioteka napędów wirtualnych: ładowanie szablonów, instancje, kopiowanie (REQ-VD-02/03/05).

Model-Author: Claude · sesja 013.

- `load_library()` czyta `plant/library/drives/*.yaml`, waliduje każdy plik (nazwa pliku =
  `id` szablonu) i zwraca słownik id → szablon.
- `resolve_instance()` buduje instancję z wpisu `machine.yaml`:
  `{id: X1, template: servo_400w, overrides: {...}}`; nadpisania (zagnieżdżone albo z kropką,
  np. `mechanics.load: 80`) są walidowane tymi samymi zakresami co szablon.
- `clone_template()` / `clone_instance()` tworzą niezależną kopię jako nowy szablon
  (`version: 1`, `based_on: <źródło>`); `save_template()` zapisuje go do biblioteki.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .drive_template import (
    ID_PATTERN,
    PARAM_BY_PATH,
    SECTIONS,
    TOP_FIELDS,
    Issue,
    TemplateError,
    validate_template,
)

LIBRARY_DIR = Path(__file__).resolve().parents[2] / "library" / "drives"
NOT_OVERRIDABLE = ("id", "version", "based_on", "name", "description", "value_source", "type",
                   "live")


@dataclass
class DriveInstance:
    """Instancja napędu w maszynie: szablon + nadpisania (po walidacji)."""

    id: str
    template_id: str
    overrides: dict[str, Any]
    params: dict[str, Any] = field(repr=False)


YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
_library_cache: dict[Path, tuple[tuple, dict[str, dict[str, Any]]]] = {}


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.load(handle, Loader=YAML_LOADER)
    except OSError as exc:
        raise TemplateError(Issue(str(path), f"nie można odczytać pliku: {exc.strerror}")) from exc
    except yaml.YAMLError as exc:
        raise TemplateError(Issue(str(path), f"niepoprawny YAML: {exc}")) from exc


def load_template_file(path: Path) -> dict[str, Any]:
    """Wczytuje i waliduje jeden plik szablonu; nazwa pliku musi odpowiadać `id`."""
    data = _read_yaml(path)
    try:
        tpl = validate_template(data)
    except TemplateError as exc:
        raise TemplateError([Issue(f"{path.name}:{i.path}" if i.path else path.name, i.message)
                             for i in exc.issues]) from None
    if path.stem != tpl["id"]:
        raise TemplateError(Issue(path.name,
                                  f"nazwa pliku musi odpowiadać id szablonu „{tpl['id']}”"))
    return tpl


def load_library(directory: Path | None = None) -> dict[str, dict[str, Any]]:
    """Ładuje wszystkie szablony z katalogu; pierwszy błędny plik przerywa z czytelnym błędem."""
    folder = LIBRARY_DIR if directory is None else Path(directory)
    if not folder.is_dir():
        raise TemplateError(Issue(str(folder), "brak katalogu biblioteki napędów"))
    paths = sorted(folder.glob("*.yaml"))
    try:
        signature = tuple((p.name, p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
    except OSError:
        signature = ()
    cached = _library_cache.get(folder)
    if signature and cached is not None and cached[0] == signature:
        return copy.deepcopy(cached[1])
    library: dict[str, dict[str, Any]] = {}
    for path in paths:
        tpl = load_template_file(path)
        library[tpl["id"]] = tpl
    if signature:
        _library_cache[folder] = (signature, copy.deepcopy(library))
    return library


def _flatten_overrides(overrides: Any, where: str, issues: list[Issue]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if overrides is None:
        return flat
    if not isinstance(overrides, dict):
        issues.append(Issue(where, "overrides musi być słownikiem"))
        return flat

    def walk(node: dict[str, Any], prefix: str) -> None:
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if path in PARAM_BY_PATH:
                flat[path] = value
            elif not prefix and key in SECTIONS and isinstance(value, dict):
                walk(value, path)
            elif not prefix and key in SECTIONS:
                issues.append(Issue(f"{where}.{path}", "sekcja nadpisań musi być słownikiem"))
            elif not prefix and key in NOT_OVERRIDABLE:
                issues.append(Issue(f"{where}.{path}", "pole nie podlega nadpisaniu "
                                                       "(zmień szablon albo sklonuj go)"))
            else:
                issues.append(Issue(f"{where}.{path}", "nieznany parametr do nadpisania"))

    walk(overrides, "")
    return flat


def apply_overrides(template: dict[str, Any], overrides: Any, where: str = "overrides"
                    ) -> dict[str, Any]:
    """Zwraca szablon z nadpisaniami; błędy mają ścieżki `where.<pole>`."""
    issues: list[Issue] = []
    flat = _flatten_overrides(overrides, where, issues)
    if issues:
        raise TemplateError(issues)
    candidate = copy.deepcopy(template)
    for path, value in flat.items():
        section, key = path.split(".", 1)
        candidate.setdefault(section, {})[key] = value
    try:
        return validate_template(candidate)
    except TemplateError as exc:
        remapped = [Issue(f"{where}.{i.path}" if i.path in flat else
                          f"{where} (po zastosowaniu nadpisań) {i.path}".rstrip(), i.message)
                    for i in exc.issues]
        raise TemplateError(remapped) from None


def resolve_instance(entry: Any, library: dict[str, dict[str, Any]], where: str = "drives[0]"
                     ) -> DriveInstance:
    """Rozwiązuje wpis instancji z machine.yaml (REQ-VD-02)."""
    if not isinstance(entry, dict):
        raise TemplateError(Issue(where, "instancja napędu musi być słownikiem"))
    issues: list[Issue] = []
    unknown = sorted(set(entry) - {"id", "template", "overrides"})
    issues += [Issue(f"{where}.{k}", "nieznane pole instancji") for k in unknown]
    inst_id = entry.get("id")
    if not isinstance(inst_id, str) or not inst_id.strip():
        issues.append(Issue(f"{where}.id", "wymagany niepusty identyfikator instancji"))
    tpl_id = entry.get("template")
    if tpl_id not in library:
        known = ", ".join(sorted(library)) or "(brak)"
        issues.append(Issue(f"{where}.template",
                            f"nieznany szablon „{tpl_id}”; dostępne: {known}"))
    if issues:
        raise TemplateError(issues)
    params = apply_overrides(library[tpl_id], entry.get("overrides"), f"{where}.overrides")
    flat = _flatten_overrides(entry.get("overrides"), "", [])
    return DriveInstance(id=inst_id, template_id=tpl_id, overrides=flat, params=params)


def resolve_instances(entries: Any, library: dict[str, dict[str, Any]]) -> dict[str, DriveInstance]:
    """Rozwiązuje listę `drives:` z machine.yaml; powtórzone id to błąd."""
    if not isinstance(entries, list):
        raise TemplateError(Issue("drives", "drives musi być listą instancji"))
    result: dict[str, DriveInstance] = {}
    issues: list[Issue] = []
    for n, entry in enumerate(entries):
        try:
            inst = resolve_instance(entry, library, f"drives[{n}]")
        except TemplateError as exc:
            issues += exc.issues
            continue
        if inst.id in result:
            issues.append(Issue(f"drives[{n}].id", f"powtórzony identyfikator „{inst.id}”"))
            continue
        result[inst.id] = inst
    if issues:
        raise TemplateError(issues)
    return result


def clone_template(source: dict[str, Any], new_id: str, *, name: str | None = None
                   ) -> dict[str, Any]:
    """Niezależna kopia szablonu pod nowym id (version 1, based_on = id źródła)."""
    if not ID_PATTERN.match(new_id):
        raise TemplateError(Issue("id", "identyfikator: małe litery, cyfry i _, od litery, "
                                        "2..48 znaków"))
    clone = copy.deepcopy(source)
    clone["id"] = new_id
    clone["version"] = 1
    clone["based_on"] = source["id"]
    clone["name"] = name or f"{source['name']} (kopia)"
    return validate_template(clone)


def clone_instance(instance: DriveInstance, new_id: str, *, name: str | None = None
                   ) -> dict[str, Any]:
    """Kopia instancji (szablon z nadpisaniami) jako nowy szablon z based_on = szablon źródłowy."""
    base = copy.deepcopy(instance.params)
    clone = clone_template(base, new_id, name=name or f"{base['name']} (kopia {instance.id})")
    clone["based_on"] = instance.template_id
    return validate_template(clone)


def dump_template(tpl: dict[str, Any]) -> str:
    """Serializuje szablon do YAML w kolejności kanonicznej (bez komentarzy)."""
    ordered: dict[str, Any] = {k: tpl[k] for k in TOP_FIELDS if k in tpl}
    for section in (*SECTIONS, "real"):     # real: napęd rzeczywisty (sesja 061)
        if section in tpl:
            ordered[section] = tpl[section]
    body = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, width=100)
    return ("# Szablon napędu wirtualnego linumeRT (kopia). Wartości przykładowe.\n"
            f"# based_on: {tpl.get('based_on')}\n" + body)


def save_template(tpl: dict[str, Any], directory: Path | None = None, *, overwrite: bool = False
                  ) -> Path:
    """Zapisuje szablon jako `<id>.yaml`; istniejący plik wymaga `overwrite=True`."""
    folder = LIBRARY_DIR if directory is None else Path(directory)
    validate_template(tpl)
    path = folder / f"{tpl['id']}.yaml"
    if path.exists() and not overwrite:
        raise TemplateError(Issue(path.name, "szablon o tym id już istnieje (użyj innej nazwy "
                                             "albo opcji --force)"))
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(dump_template(tpl), encoding="utf-8")
    except OSError as exc:
        raise TemplateError(Issue(str(path), f"nie można zapisać pliku: {exc.strerror}")) from exc
    return path
