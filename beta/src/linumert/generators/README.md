# linumert.generators

Generatory cykli (programowanie dialogowe). Sesja 039: klasa bazowa i rejestr; generatory
wbudowane (nagłówek, koniec, narzędzie, planowanie, kieszenie, wiercenie, rowki, kontur) w sesjach 040–043.

- `base.py`: `BaseMacroGenerator` (`name`, `version`, `title`, `fields`, `validate()` → lista `Issue`
  z kodami P- katalogu alarmów, `check()` dla reguł między polami, `generate()`, `preview_2d()`),
  `Field` (float, int, bool, choice, text; zakresy, wartości domyślne), `fmt()` — liczby dla G-code.
  Zgodność: `is_valid(params) -> bool`, `generate_ngc(params, filename) -> str`.
- `registry.py`: `GeneratorRegistry` — nazwa + wersja → klasa; kompilator bierze dokładnie wersję
  zapisaną w kroku (P-5011, gdy jej brak), więc stary program daje ten sam G-code.
- `tooling.py`: `check_steps()` — kroki programu z bazą narzędzi: `tool_change` ustala narzędzie,
  kolejne kroki sprawdzają typ (P-5207), średnicę i skok (P-5208), długość ostrza / wysokość
  głowicy (P-5209), obroty i kierunek (P-5210, P-5211), brak narzędzia w bazie (P-5206).
  Kompilator: `compile_program(..., tools=ToolDB(...).get)`; bez `tools` nic nie jest sprawdzane.

Zasady: wyłącznie tekst G-code LinuxCNC; podprogramy `o<nazwa> call`; bez M98/M99 i bez M2/M30
(koniec dopisuje kompilator); wynik zależy tylko od parametrów i wersji.

## Generatory konturowe (sesja 043, `contours.py`)
`slot_linear`, `slot_arc` (rowki: oś + obwiednie, wejście pionowe albo rampa po osi), `stud_rect`,
`stud_circle` (czopy od marginesu do ściany, współ- lub przeciwbieżnie), `contour` (odcinki i łuki
z tekstu, korekcja G41.1/G42.1 z D frezu, styczny dojazd/odjazd, P-5010 przy nieciągłości).
Golden: `tests/golden/contours_*.ngc`; geometria sprawdzana materiałem `StockMap`.
