"""Generate roadmap views from the single status registry (stdlib only).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import json
import posixpath
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'docs/roadmap/plan.json'
MARKER = '<!-- ROADMAP_DATA -->'
README_START = '<!-- MILESTONES:START -->'
README_END = '<!-- MILESTONES:END -->'


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
    return f'[{ref}]({posixpath.relpath(ref, base)})'


def summary(plan: dict) -> str:
    counts = Counter(s['status'] for s in plan['sessions'])
    labels = plan['policy']['status_labels']
    return '; '.join(f'{labels[status]}: {counts[status]}' for status in labels)


def readme_milestones(plan: dict, text: str) -> str:
    """Refresh only the marked public summary; counts never certify a gate."""
    if text.count(README_START) != 1 or text.count(README_END) != 1:
        raise ValueError('README wymaga jednej pary znaczników MILESTONES')
    before, _, rest = text.partition(README_START)
    old, _, after = rest.partition(README_END)
    if README_START in old or README_END in before:
        raise ValueError('Niepoprawna kolejność znaczników MILESTONES')
    done = sum(r['status'] == 'done' for r in plan['sessions'])
    lines = ['', '<!-- Generowane przez tools/roadmap.py z plan.json. -->', '',
             f"Stan rejestru: **{plan['updated']} · {done}/{plan['original_count']} "
             'ukończonych sesji**.', '',
             '| Kamień | Zakres | Sesje ukończone | Rekordy z otwartymi kryteriami |',
             '|---|---|---:|---:|']
    for milestone in plan['milestones']:
        group = [r for r in plan['sessions'] if r['milestone'] == milestone['id']]
        ids = {r['id'] for r in group}
        extensions = [r for r in plan['extensions'] if ids.intersection(r['parents'])]
        count = sum(r['status'] == 'done' for r in group)
        remaining = sum(bool(r['remaining']) for r in group + extensions)
        lines.append(f"| {milestone['id']} | {milestone['name']} | {count}/{len(group)} "
                     f'| {remaining} |')
    lines += ['', 'Licznik sesji nie oznacza zaliczenia bramki, odbioru stanowiska ani sprzętu. '
              'Otwarte kryteria obejmują sesje i powiązane rozszerzenia; jedno rozszerzenie '
              'może dotyczyć kilku kamieni.', '',
              '[Pełny plan, kryteria i dowody](docs/roadmap/PLAN.md) · '
              '[Roadmapa HTML](docs/roadmap/index.html) · '
              '[Źródłowy rejestr](docs/roadmap/plan.json)', '']
    return before + README_START + '\n'.join(lines) + README_END + after


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
        title = f"[{row['title']}]({posixpath.relpath(row['prompt'], base)})"
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


def progress_svg(plan: dict) -> str:
    """README chart: original sessions only, never infer acceptance from counts.

    Palette follows docs/design/tokens.yaml (bg, panel, line, fg, fg2, teal).
    Plain SVG keeps the GitHub view sharp without fonts, scripts or remote assets.
    """
    rows = plan['sessions']
    counts = Counter(row['status'] for row in rows)
    done, total = counts['done'], plan['original_count']
    percent = f'{100 * done / total:.1f}'.replace('.', ',')
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700" '
           'viewBox="0 0 1200 700" role="img" aria-labelledby="title desc">',
           f'<title id="title">linumeRT — ukończone sesje: {done}/{total}</title>',
           '<desc id="desc">Postęp sesji M0–M6 z rejestru plan.json. '
           'Licznik sesji nie oznacza zaliczenia bramek ani odbioru sprzętu.</desc>',
           '<rect width="1200" height="700" rx="24" fill="#0a0c0f"/>',
           '<g font-family="sans-serif" fill="#e8eef4">',
           '<text x="56" y="55" fill="#2dd4bf" font-size="18" '
           'letter-spacing="3">linumeRT / STAN PROJEKTU</text>',
           '<text x="56" y="111" font-size="38" font-weight="700">'
           'Ukończone sesje pierwotnego planu</text>',
           f'<text x="56" y="195" font-size="64" font-weight="700">{done} / {total}</text>',
           f'<text x="344" y="192" font-size="28" fill="#2dd4bf">{percent}%</text>',
           f'<text x="1144" y="190" text-anchor="end" font-size="18" '
           f'fill="#9aa7b4">Stan rejestru: {escape(plan["updated"])}</text>',
           '<rect x="56" y="219" width="1088" height="10" rx="5" fill="#26303a"/>',
           f'<rect x="56" y="219" width="{1088 * done / total:.2f}" height="10" '
           'rx="5" fill="#2dd4bf"/>']
    for index, milestone in enumerate(plan['milestones']):
        group = [r for r in rows if r['milestone'] == milestone['id']]
        n = sum(r['status'] == 'done' for r in group)
        y = 270 + index * 45
        width = 370 * n / len(group) if group else 0
        svg += [f'<text x="56" y="{y}" font-size="18" font-weight="700">'
                f'{escape(milestone["id"])}</text>',
                f'<text x="108" y="{y}" font-size="17" fill="#9aa7b4">'
                f'{escape(milestone["name"])}</text>',
                f'<rect x="682" y="{y - 15}" width="370" height="14" '
                'rx="7" fill="#26303a"/>',
                f'<rect x="682" y="{y - 15}" width="{width:.2f}" height="14" '
                'rx="7" fill="#2dd4bf"/>',
                f'<text x="1144" y="{y}" text-anchor="end" font-size="18">'
                f'{n} / {len(group)}</text>']
    svg += ['<path d="M56 586 H1144" stroke="#26303a"/>',
            f'<text x="56" y="620" font-size="18">Częściowe: {counts["partial"]} '
            f' · W toku: {counts["in_progress"]} · Planowane: {counts["planned"]} '
            f' · Do odbioru: {counts["acceptance"]} · Zablokowane: {counts["blocked"]}</text>',
            '<text x="56" y="655" font-size="16" fill="#9aa7b4">'
            'Ukończone sesje ≠ zaliczone bramki, odbiór pulpitu, RT lub sprzętu.</text>',
            '</g></svg>']
    return '\n'.join(svg) + '\n'


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
            'README.md': readme_milestones(plan, (root / 'README.md').read_text()),
            'docs/roadmap/PLAN.md': detail, 'docs/roadmap/index.html': page,
            'docs/raporty/postep-sesji.svg': progress_svg(plan)}


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
