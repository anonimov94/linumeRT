# linumert.generators

Generatory cykli (programowanie dialogowe). Sesja 039: klasa bazowa i rejestr; generatory
wbudowane (nagłówek, koniec, narzędzie, planowanie, kieszenie, wiercenie, rowki, kontur) w sesjach 040–043.

- `base.py`: `BaseMacroGenerator` (`name`, `version`, `title`, `fields`, `validate()` → lista `Issue`
  z kodami P- katalogu alarmów, `check()` dla reguł między polami, `generate()`, `preview_2d()`),
  `Field` (float, int, bool, choice, text; zakresy, wartości domyślne), `fmt()` — liczby dla G-code.
  Zgodność: `is_valid(params) -> bool`, `generate_ngc(params, filename) -> str`.
- `registry.py`: `GeneratorRegistry` — nazwa + wersja → klasa; kompilator bierze dokładnie wersję
  zapisaną w kroku (P-5011, gdy jej brak), więc stary program daje ten sam G-code.

Zasady: wyłącznie tekst G-code LinuxCNC; podprogramy `o<nazwa> call`; bez M98/M99 i bez M2/M30
(koniec dopisuje kompilator); wynik zależy tylko od parametrów i wersji.
