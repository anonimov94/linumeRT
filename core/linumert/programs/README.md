# linumert.programs

Format programów dialogowych `.lnx`, kompilator `.lnx → .ngc`, przygotówka. Sesja 039.

| Moduł | Zawartość |
|---|---|
| `lnx.py` | model `.lnx` (Pydantic, JSON, `schema_version: 1`), wczytywanie z błędami po polsku (P-5012), zapis atomowy, `lnx_schema.json` generowany z modelu (`write_schema()`, test zgodności) |
| `stock.py` | przygotówka BOX/CYL i linia `;@STOCK` (postać kanoniczna, parsowanie bezstratne) |
| `compiler.py` | `compile_program()` / `compile_file()`: deterministyczny `.ngc` (komentarze kroków, wersje generatorów, `;@STOCK`, G21/G20, `M2`); błąd dowolnego kroku blokuje zapis; kontrola wyjścia generatorów (P-5013: M98/M99, M2/M30, nowa linia, niezamknięty komentarz) |

Generatory: `linumert.generators` (`BaseMacroGenerator`, rejestr wersji). Testy: `tests/test_lnx.py`
(golden `tests/golden/lnx_program.ngc`), `tests/test_ngc_linuxcnc.py` (interpreter `rs274` z LinuxCNC 2.9).
`lexer.py` to lekser G-code LinuxCNC 2.9 (sesja 044, kody P-5101…P-5111), a `linuxcnc_check.py` kontroluje
program interpreterem `rs274` (test z markerem `linuxcnc`). Opis: `docs/GCODE_LEKSER.md`.

`job.py` przygotowuje deterministyczny pakiet `linumert.job` v1: źródło `.lnx`, G-code,
model maszyny i rozwiązane napędy, użyte narzędzia i `tool.tbl`, ustawienie detalu,
raport przygotowania oraz manifest SHA-256. `render()` przyjmuje zwalidowany model
i snapshot napędów/narzędzi; `publish()` odmawia nadpisania, `read()` kontroluje integralność.
Początkowy zakres: header/tool_change/face_mill/pocket_rect/pocket_circle/drill_holes/program_end.
Układ G54–G59 i jego zero są zapisane w mm układu maszyny, przed korekcją długości.
Przygotowanie nie zalicza interpretera, limitów ruchu ani materiału: raport ma `pending`.
`prepare.py` jest wspólnym adapterem CLI (`linumert-job`) i WebHMI. Konfiguracja wejść,
zakres i odbiór operatora: `docs/WORKFLOW_ZADANIA.md`, VERTICAL-PREPARE w rejestrze.
