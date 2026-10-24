#!/usr/bin/env bash
# Tłumaczenia ekranu linumeRT (sesja 007). Model-Author: Claude · 2026-10-24.
#   tools/i18n.sh          # aktualizuje screens/linumert/i18n/linumert_pl.ts z wywołań translate()
#   tools/i18n.sh --qm     # dodatkowo kompiluje .qm (lrelease z qttools5-dev-tools)
# Nowe teksty trafiają do .ts jako "unfinished"; uzupełnij <translation> i usuń type.
# Kontrola kompletności: python3 tools/i18n_check.py (także w testach).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/screens/linumert/i18n"
mkdir -p "$DIR"
command -v pylupdate5 >/dev/null || { echo "Brak pylupdate5 (pakiet pyqt5-dev-tools)." >&2; exit 1; }
mapfile -t SOURCES < <(grep -l -E '\b_?translate\(' "$ROOT"/screens/linumert/*.py | sort)
pylupdate5 -noobsolete "${SOURCES[@]}" -ts "$DIR/linumert_pl.ts"
if [[ "${1:-}" == "--qm" ]]; then
    LRELEASE="$(command -v lrelease || command -v lrelease-qt5 || true)"
    [[ -n "$LRELEASE" ]] || { echo "Brak lrelease (pakiet qttools5-dev-tools); ekran użyje .ts." >&2; exit 1; }
    "$LRELEASE" "$DIR/linumert_pl.ts" -qm "$DIR/linumert_pl.qm"
fi
python3 "$ROOT/tools/i18n_check.py"
