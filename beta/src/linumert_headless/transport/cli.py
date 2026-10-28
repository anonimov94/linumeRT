"""Transport CLI: ``linumertctl <domena> <akcja> [--parametr wartość]``.

SPDX-License-Identifier: GPL-2.0-or-later

CLI jest zbudowane **z kontraktu**, nie z ręcznej listy poleceń: nazwy podpoleceń,
parametry i walidacja pochodzą z rejestru operacji. Dzięki temu nowa funkcja backendu
jest od razu dostępna z terminala i z GUI — bez dopisywania drugiego interfejsu.

Dwa tryby:
- lokalny (domyślnie): aplikacja działa w tym procesie — wygodne w skryptach i CI,
- zdalny (``--url``): te same operacje przez REST działającego ``linumertd``.

Przykłady::

    linumertctl system info
    linumertctl machine state
    linumertctl machine home --axis X
    linumertctl program estimate --name linumert_demo.ngc
    linumertctl contract --out api/contract.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ..app import build_application
from ..config import AppConfig
from ..errors import ApiError

PARAM_SEPARATOR = "="


def _coerce(value: str) -> Any:
    """Napis z terminala → JSON: liczby, true/false/null, listy i obiekty JSON."""
    text = value.strip()
    lowered = text.lower()
    if lowered in {"true", "false", "null"}:
        return {"true": True, "false": False, "null": None}[lowered]
    if text.startswith(("[", "{")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_params(pairs: list[str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for pair in pairs:
        if PARAM_SEPARATOR not in pair:
            raise SystemExit(f"parametr bez '=': {pair!r} (oczekiwano nazwa=wartość)")
        key, _, raw = pair.partition(PARAM_SEPARATOR)
        params[key.strip()] = _coerce(raw)
    return params


class RemoteClient:
    """Minimalny klient REST — bez zależności poza stdlib (``urllib``)."""

    def __init__(self, url: str, token: str = "", timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def call(self, command: str, params: dict[str, Any]) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        request = urllib.request.Request(
            f"{self.url}/api/v1/call",
            data=json.dumps({"command": command, "params": params}).encode("utf-8"),
            headers={"content-type": "application/json",
                     **({"x-lrt-token": self.token} if self.token else {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return json.loads(exc.read().decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {"ok": False, "error": {"code": "http_error",
                                               "message": f"HTTP {exc.code}"}}


def build_parser(contract: Any) -> argparse.ArgumentParser:
    """Parser z operacji kontraktu: ``domena akcja parametry``."""
    parser = argparse.ArgumentParser(
        prog="linumertctl",
        description="CLI aplikacji linumeRT headless — te same operacje co REST i GUI.",
        epilog="Parametry podaj jako nazwa=wartość, np. --axis X. "
               "Listę operacji pokazuje `linumertctl operations`.",
    )
    parser.add_argument("--url", default="", help="zdalny serwer, np. http://127.0.0.1:8080")
    parser.add_argument("--token", default="", help="token API (albo LRT_TOKEN)")
    parser.add_argument("--backend", default="fake", choices=("fake", "linuxcnc"),
                        help="backend maszyny w trybie lokalnym (domyślnie fake)")
    parser.add_argument("--root", default="", help="katalog projektu beta (domyślnie ten repo)")
    parser.add_argument("--json", action="store_true", help="zawsze drukuj pełny JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    for operation in contract.operations():
        domain, _, action = operation.name.partition(".")
        command = sub.add_parser(
            operation.name, help=operation.summary,
            description=f"{operation.summary}\n\nstatus: {operation.status}"
                        + (f"\nplan: {operation.plan}" if operation.plan else ""),
        )
        command.add_argument("params", nargs="*", metavar="nazwa=wartość",
                             help="parametry operacji (schemat: `linumertctl contract`)")
        command.set_defaults(operation=operation.name)

    extra = sub.add_parser("operations", help="lista operacji (bez schematów)")
    extra.set_defaults(operation="@operations")
    extra_contract = sub.add_parser("contract", help="pełny kontrakt JSON")
    extra_contract.add_argument("--out", default="", help="zapisz do pliku zamiast na stdout")
    extra_contract.set_defaults(operation="@contract")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punkt wejścia ``linumertctl``; kod wyjścia 0 = sukces, 1 = błąd operacji."""
    config = AppConfig()
    bootstrap = build_application(config)  # kontrakt jest taki sam lokalnie i zdalnie
    parser = build_parser(bootstrap.contract)
    args = parser.parse_args(argv)
    bootstrap.stop()

    if args.operation == "@operations":
        payload = {"domains": bootstrap.contract.domains(),
                   "operations": [{"name": o.name, "kind": o.kind, "status": o.status,
                                   "safety": o.safety, "role": o.role, "summary": o.summary}
                                  for o in bootstrap.contract.operations()]}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.operation == "@contract":
        payload = bootstrap.contract.export(application="linumeRT headless",
                                            version=_version())
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if args.out:
            target = Path(args.out)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            print(f"zapisano kontrakt: {target} ({len(payload['operations'])} operacji)")
        else:
            print(text)
        return 0

    try:
        params = _parse_params(args.params)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.url:
        response = RemoteClient(args.url, args.token).call(args.operation, params)
        if not response.get("ok", False):
            error = response.get("error", {})
            print(f"błąd {error.get('code', '?')}: {error.get('message', response)}",
                  file=sys.stderr)
            return 1
        print(_format(response.get("result", {}), args.json))
        return 0

    cfg = AppConfig(backend=args.backend, root=Path(args.root) if args.root else config.root,
                    token=args.token)
    app = build_application(cfg)
    try:
        result = app.call(args.operation, params, channel="cli", token=args.token)
    except ApiError as exc:
        print(f"błąd {exc.code}: {exc.message}", file=sys.stderr)
        for key, value in exc.details.items():
            print(f"  {key}: {value}", file=sys.stderr)
        return 1
    finally:
        app.stop()
    print(_format(result.model_dump(mode="json"), args.json))
    return 0


def _format(payload: Any, as_json: bool) -> str:
    if as_json or not isinstance(payload, dict):
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines = []
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _version() -> str:
    from .. import __version__

    return __version__


__all__ = ["RemoteClient", "build_parser", "main"]
