"""Generate roadmap views from the single status registry (stdlib only).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'docs/roadmap/plan.json'
MARKER = '<!-- ROADMAP_DATA -->'


def validate(plan: dict, root: Path) -> None:
    """Fail before writing any view if IDs, references or evidence are invalid."""
    if plan['schema_version'] != 1 or plan['original_count'] != 84:
        raise ValueError('Nieobsługiwana wersja lub zmieniona liczba pierwotnych sesji')
    sessions, extensions = plan['sessions'], plan['extensions']
    original_ids = [f'{n:03}' for n in range(1, 85)]
    if [s['id'] for s in sessions] != original_ids:
        raise ValueError('Pierwotne sesje muszą zachować ID 001–084 i kolejność')
    rows = sessions + extensions
    ids = [s['id'] for s in rows]
    aliases = [alias for s in extensions for alias in s.get('aliases', [])]
    if len(set(ids + aliases)) != len(ids + aliases):
        raise ValueError('Powtórzone ID lub alias')
    milestones = [m['id'] for m in plan['milestones']]
    if milestones != [f'M{n}' for n in range(7)]:
        raise ValueError('Wymagane kamienie M0–M6')
    labels = plan['policy']['status_labels']
    if set(labels) != {'planned', 'in_progress', 'partial', 'acceptance', 'done', 'blocked'}:
        raise ValueError('Niepoprawny słownik statusów')
    for row in rows:
        if row['status'] not in labels or not row['progress'].strip():
            raise ValueError(f"Niepoprawny status/opis: {row['id']}")
        if row['status'] in {'partial', 'acceptance', 'blocked'} and not row['remaining']:
            raise ValueError(f"Brak otwartych kryteriów/blokady: {row['id']}")
        if row in sessions:
            if row['milestone'] not in milestones:
                raise ValueError(f"Nieznany kamień: {row['id']}")
            expected = f"prompts/sesja-{row['id']}.md"
            if row['prompt'] != expected:
                raise ValueError(f'Niepoprawny prompt: {expected}')
        else:
            if not row['parents'] or not set(row['parents']) <= set(original_ids):
                raise ValueError(f"Rozszerzenie bez poprawnej sesji nadrzędnej: {row['id']}")
            if row['status'] != 'done' and not row['remaining']:
                raise ValueError(f"Brak następnego kroku: {row['id']}")
        if row['status'] in {'done', 'partial', 'acceptance'} and not row['evidence']:
            raise ValueError(f"Brak dowodów: {row['id']}")
        for ref in row['evidence'] + ([row['prompt']] if row.get('prompt') else []):
            if ref.startswith('https://'):
                continue
            path = (root / ref.split('#', 1)[0]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(f"Nieistniejący/niebezpieczny odsyłacz {row['id']}: {ref}")


def link(ref: str, base: str) -> str:
    if ref.startswith('https://'):
        return f'[PR]({ref})'
    return f'[{ref}]({os.path.relpath(ref, base)})'


def summary(plan: dict) -> str:
    counts = Counter(s['status'] for s in plan['sessions'])
    labels = plan['policy']['status_labels']
    return '; '.join(f'{labels[status]}: {counts[status]}' for status in labels)


def table(plan: dict, base: str, *, detailed: bool = False) -> str:
    lines = ['## Kamienie pierwotnego planu', '',
             '| Kamień | Cel | Kryterium bramki (cel, nie wynik odbioru) |', '|---|---|---|']
    for milestone in plan['milestones']:
        lines.append(f"| {milestone['id']} — {milestone['name']} | {milestone['goal']} "
                     f"| {milestone['gate']} |")
    lines += ['', '## Sesje 001–084', '',
              '| ID | Kamień | Zakres | Stan |', '|---|---|---|---|']
    labels = plan['policy']['status_labels']
    for row in plan['sessions']:
        title = f"[{row['title']}]({os.path.relpath(row['prompt'], base)})"
        lines.append(f"| {row['id']} | {row['milestone']} | {title} | {labels[row['status']]} |")
    lines += ['', '## Rozszerzenia włączone do pierwotnych sesji', '',
              'Nie są kolejnym harmonogramem. Ich status dotyczy tylko wskazanego kroku.', '',
              '| ID (dawny alias) | Sesje nadrzędne | Zakres | Stan |', '|---|---|---|---|']
    for row in plan['extensions']:
        aliases = ', '.join(row.get('aliases', []))
        name = row['id'] + (f' ({aliases})' if aliases else '')
        lines.append(f"| {name} | {', '.join(row['parents'])} | {row['title']} "
                     f"| {labels[row['status']]} |")
    if detailed:
        lines += ['', '## Postęp, pozostały zakres i dowody', '']
        for row in plan['sessions'] + plan['extensions']:
            lines += [f"### {row['id']} — {row['title']}", '',
                      f"**{labels[row['status']]}**. {row['progress']}", '']
            if row.get('gate'):
                lines += [f"Bramka automatyczna: `{row['gate']}`; odbiór stanowiska osobno.", '']
            if row['remaining']:
                lines += ['Pozostaje: ' + ' '.join(row['remaining']), '']
            refs = row['evidence'] + ([row['prompt']] if row.get('prompt') else [])
            if refs:
                lines += ['Źródła: ' + ', '.join(link(ref, base) for ref in refs) + '.', '']
    return '\n'.join(lines) + '\n'


def outputs(plan: dict, root: Path) -> dict[str, str]:
    banner = ('<!-- Generowane przez python3 tools/roadmap.py; '
              'edytuj docs/roadmap/plan.json. -->\n')
    intro = (f"Pierwotny plan: **84 sesje M0–M6**, commit `{plan['origin_commit']}`. "
             f"Stan na {plan['updated']}: {summary(plan)}.\n\n"
             'Zakończenie części implementacji nie oznacza odbioru całej funkcji ani sprzętu.\n\n')
    readme = (banner + '# Prompty i wspólna roadmapa linumeRT\n\n' + intro
              + 'Jedyne źródło statusów, powiązań i pozostałej pracy: '
              '[plan.json](../docs/roadmap/plan.json). Zasady aktualizacji: '
              '[instrukcja roadmapy](../docs/roadmap/README.md). '
              'Szczegóły i dowody: [PLAN.md](../docs/roadmap/PLAN.md); '
              '[widok HTML](../docs/roadmap/index.html).\n\n'
              + table(plan, 'prompts'))
    completed = [r for r in plan['sessions'] if r['status'] == 'done']
    done = (banner + '# Ukończone zakresy — widok rejestru\n\n' + intro
            + 'To wynik generatora, nie lista do ręcznego dopisywania. Wybór pracy i statusy '
            'są w [plan.json](../docs/roadmap/plan.json); częściowe zakresy w '
            '[PLAN.md](../docs/roadmap/PLAN.md).\n\n'
            + f"Ukończone pierwotne sesje: **{len(completed)} z 84**.\n\n")
    for row in completed:
        done += f"{row['id']} | {row.get('historical_completion', row['progress'])}\n"
    done += '\n## Ukończone rozszerzenia (nie zamykają automatycznie sesji)\n\n'
    for row in plan['extensions']:
        if row['status'] == 'done':
            done += f"{row['id']} | {row['progress']}\n"
    done += ('\n## Korekty historycznego rejestru\n\n'
             '007 i 048 były wpisane jako wykonane mimo odłożonego zakresu; teraz są częściowe. '
             'Dawne wpisy zachowano w polu `historical_completion` rejestru i historii Git. '
             'Numery 085–088 i oznaczenia konkursowe są aliasami rozszerzeń, '
             'nie nowymi sesjami pierwotnego planu.\n')
    detail = (banner + '# Wspólny plan linumeRT\n\n' + intro
              + table(plan, 'docs/roadmap', detailed=True))
    payload = json.loads(json.dumps(plan))
    for row in payload['sessions'] + payload['extensions']:
        if row.get('prompt'):
            row['prompt_text'] = (root / row['prompt']).read_text()
    encoded = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')
    template = (root / 'docs/roadmap/template.html').read_text()
    if template.count(MARKER) != 1:
        raise ValueError('Szablon wymaga dokładnie jednego znacznika danych')
    page = template.replace(MARKER, f'<script id="plan" type="application/json">{encoded}</script>')
    return {'prompts/README.md': readme, 'prompts/DONE.md': done,
            'docs/roadmap/PLAN.md': detail, 'docs/roadmap/index.html': page}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail on stale generated views')
    args = parser.parse_args()
    try:
        plan = json.loads((ROOT / SOURCE).read_text())
        validate(plan, ROOT)
        views = outputs(plan, ROOT)
        stale = []
        for name, content in views.items():
            path = ROOT / name
            if not path.exists() or path.read_text() != content:
                stale.append(name)
                if not args.check:
                    path.write_text(content)
        if args.check and stale:
            print('Nieaktualne widoki: ' + ', '.join(stale))
            return 1
        print(f'Roadmapa: 84 sesje, {len(plan["extensions"])} rozszerzeń; {summary(plan)}')
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'Błąd roadmapy: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
