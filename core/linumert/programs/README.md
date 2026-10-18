# linumert.programs

Format programów dialogowych `.lnx`, kompilator `.lnx → .ngc`, przygotówka. Sesja 039.

| Moduł | Zawartość |
|---|---|
| `lnx.py` | model `.lnx` (Pydantic, JSON, `schema_version: 1`), wczytywanie z błędami po polsku (P-5012), zapis atomowy, `lnx_schema.json` generowany z modelu (`write_schema()`, test zgodności) |
| `stock.py` | przygotówka BOX/CYL i linia `;@STOCK` (postać kanoniczna, parsowanie bezstratne) |
| `compiler.py` | `compile_program()` / `compile_file()`: deterministyczny `.ngc` (komentarze kroków, wersje generatorów, `;@STOCK`, G21/G20, `M2`); błąd dowolnego kroku blokuje zapis; kontrola wyjścia generatorów (P-5013: M98/M99, M2/M30, nowa linia, niezamknięty komentarz) |

Generatory: `linumert.generators` (`BaseMacroGenerator`, rejestr wersji). Testy: `tests/test_lnx.py`
(golden `tests/golden/lnx_program.ngc`), `tests/test_ngc_linuxcnc.py` (interpreter `rs274` z LinuxCNC 2.9).
