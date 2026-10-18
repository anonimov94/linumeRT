#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Model-Author: Claude · autozapis pracy (prośba właściciela 2026-10-18).
# Co INTERVAL sekund (domyślnie 600): commit i push bieżącej gałęzi wip/* albo claude/*.
# Pomija main, gałęzie innych modeli, pliki > MAX_KB (domyślnie 1024 KB) i wszystko z .gitignore.
#   tools/dev/autozapis.sh            # pętla
#   tools/dev/autozapis.sh --raz      # jeden przebieg
set -uo pipefail
cd "$(dirname "$0")/../.."
INTERVAL=${INTERVAL:-600}
MAX_KB=${MAX_KB:-1024}
once() {
  local branch big n
  branch=$(git symbolic-ref --short -q HEAD) || return 0
  [[ $branch == wip/* || $branch == claude/* ]] || { echo "autozapis: pomijam gałąź $branch"; return 0; }
  [[ -e .git/MERGE_HEAD || -d .git/rebase-merge || -d .git/rebase-apply ]] && return 0
  git add -A
  while IFS= read -r f; do
    [[ -f $f ]] || continue
    big=$(( $(stat -c %s "$f") / 1024 ))
    if (( big > MAX_KB )); then git reset -q -- "$f"; echo "autozapis: pomijam $f (${big} KB)"; fi
  done < <(git diff --cached --name-only --diff-filter=AM)
  n=$(git diff --cached --name-only | wc -l)
  if (( n > 0 )); then
    git commit -q -m "wip: autozapis $(date -u +%FT%H:%MZ) ($n plików)

Model-Author: Claude

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || return 0
  fi
  if [[ -n $(git log --oneline "@{u}..HEAD" 2>/dev/null) ]] || ! git rev-parse -q --verify "@{u}" >/dev/null; then
    git push -q -u origin "$branch" 2>&1 | grep -v '^remote:' || true
    echo "autozapis: $(date +%T) $branch wypchnięta"
  fi
}
if [[ ${1:-} == --raz ]]; then once; exit; fi
while true; do once; sleep "$INTERVAL"; done
