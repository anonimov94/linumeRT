# linumert.tools

Baza narzędzi: SQLite jako źródło prawdy (D13), atomowy eksport `tool.tbl` dla LinuxCNC. Sesja 032.

| Moduł | Zawartość |
|---|---|
| `types.py` | 10 typów z `docs/wymagania/NARZEDZIA_I_KOLIZJE.md` §1 (parametry wymagane i opcjonalne, reguły: ostrze ≤ L, R naroża ≤ D/2, szyjka < D, kąt ≤ 180°), błędy P-5201/P-5205 |
| `tbl.py` | `tool.tbl` (T P X…W D I J Q ;komentarz): odczyt z błędami linii (P-5204), zapis kanoniczny bez strat, przeliczenie mm ↔ cale (`scale_entries`) |
| `db.py` | `ToolDB`: migracje (`PRAGMA user_version`), dodawanie/edycja/usuwanie z historią (stan przed/po, źródło, czas z zegara), unikalne T i P (P-5202/P-5203), eksport/import `tool.tbl` w jednostkach maszyny (atomowo; import zachowuje typ i geometrię), CSV |

Narzędzie bez typu jest dozwolone (import z `tool.tbl`), symulacja użyje walca zastępczego (K-320).
`tool.tbl` jest zawsze w jednostkach maszyny (`LINEAR_UNITS` z INI): `export_tbl(path, units="inch")`.
Ekran (zakładka narzędzi, dialog typu, przeładowanie tabeli w LinuxCNC) — po kopii ekranu (sesja 005).
Testy: `tests/test_tools_db.py` (z markerem `linuxcnc`: tabela z bazy w interpreterze rs274, G43).
