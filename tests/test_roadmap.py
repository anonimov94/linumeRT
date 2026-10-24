"""Roadmap integrity: prevent lost scope, false completion and stale public views.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('roadmap', ROOT / 'tools/roadmap.py')
roadmap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(roadmap)


@pytest.fixture
def plan():
    return json.loads((ROOT / roadmap.SOURCE).read_text())


def test_public_views_match_registry_and_current_prompts(plan):
    roadmap.validate(plan, ROOT)
    for path, expected in roadmap.outputs(plan, ROOT).items():
        assert (ROOT / path).read_text() == expected, f'Regenerate {path}'


@pytest.mark.parametrize(
    'mutation', ['missing_session', 'duplicate_alias', 'orphan', 'no_evidence', 'empty_blocker']
)
def test_invalid_registry_is_rejected(plan, mutation):
    if mutation == 'missing_session':
        plan['sessions'].pop(20)
    elif mutation == 'duplicate_alias':
        plan['extensions'][0]['aliases'] = ['001']
    elif mutation == 'orphan':
        plan['extensions'][0]['parents'] = ['999']
    elif mutation == 'no_evidence':
        plan['sessions'][0]['evidence'] = []
    else:
        plan['sessions'][0]['status'] = 'blocked'
        plan['sessions'][0]['remaining'] = []
    with pytest.raises(ValueError):
        roadmap.validate(plan, ROOT)


@pytest.mark.parametrize('reference', ['../../etc/passwd', 'missing-evidence.md'])
def test_missing_or_escaping_local_evidence_is_rejected(plan, reference):
    plan['sessions'][0]['evidence'] = [reference]
    with pytest.raises(ValueError):
        roadmap.validate(plan, ROOT)


def test_completed_extension_does_not_close_parent_or_gate(plan):
    before = copy.deepcopy(plan['sessions'])
    for row in plan['extensions']:
        row['status'] = 'done'
    roadmap.outputs(plan, ROOT)
    assert plan['sessions'] == before
    assert next(s for s in plan['sessions'] if s['id'] == '038')['gate'] == 'open'


def test_prompt_change_is_detected_and_html_script_is_not_injectable(plan, tmp_path):
    prompt = tmp_path / 'prompts/sesja-001.md'
    prompt.parent.mkdir()
    prompt.write_text('new prompt </script><script>alert(1)</script>')
    template = tmp_path / 'docs/roadmap/template.html'
    template.parent.mkdir(parents=True)
    template.write_text(roadmap.MARKER)
    plan['sessions'] = plan['sessions'][:1]
    plan['extensions'] = []
    page = roadmap.outputs(plan, tmp_path)['docs/roadmap/index.html']
    assert 'new prompt' in page
    assert '</script><script>alert' not in page
    assert r'\u003c/script>' in page
