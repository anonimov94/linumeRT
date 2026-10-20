# Lekser i kontrola G-code LinuxCNC (sesja 044)

Model-Author: Claude · 2026-10-18

`core/linumert/programs/lexer.py` sprawdza składnię programów `.ngc` bez LinuxCNC; błędy mają
kod z katalogu alarmów (P-5101…P-5111), linię i kolumnę (od 1, w oryginalnej linii — także gdy
w kodzie są spacje). `check(text)` zwraca listę błędów, `lex(text)` także rozbiór linii
(słowa, przypisania parametrów, komentarze, słowo O, `/`, `%`).

| Kod | Błąd |
|---|---|
| P-5101 | niezamknięty komentarz albo samotny `)` |
| P-5102 | komentarz w komentarzu |
| P-5103 | znak, który nie jest słowem (np. `$`) |
| P-5104 | brak wartości po literze |
| P-5105 | niepoprawna liczba (`1.2.3`) |
| P-5106 | `[` bez pary |
| P-5107 | nieznana funkcja albo operator |
| P-5108 | niepoprawny parametr albo przypisanie bez `=` |
| P-5109 | słowo O: brak słowa kluczowego, argumenty, parowanie bloków w całym pliku |
| P-5110 | niepoprawne wyrażenie (puste, brak operatora, `ATAN[a]/[b]`) |
| P-5111 | `N` poza początkiem linii |

**Zgodność z LinuxCNC.** `tests/data/gcode_samples.yaml` (44 próbki) — test z markerem `linuxcnc`
porównuje werdykt leksera z interpreterem `rs274` LinuxCNC 2.9 (`linuxcnc_check.py`):
- `same` — ten sam werdykt (większość próbek);
- `strict` — lekser celowo surowszy: rs274 przyjmuje `#<>=1`, samotne `o100` i niezamknięte
  `o1 if` przed `M2`, a przy różnych etykietach `o1 while [0]` … `o2 endwhile` **zawiesza się**
  (szuka końca pętli bez końca) — dlatego `check_with_linuxcnc` ma limit czasu;
- `semantic` — składnia poprawna, błąd zgłasza dopiero interpreter (np. `G0 E1`: E jest słowem
  w 2.9, ale wymaga G70/G76/M66–M68; `G1` bez posuwu).

**Interpreter LinuxCNC** (`linuxcnc_check.check_with_linuxcnc`): gdy jest RIP (`LINUXCNC_DIR`)
albo `rs274` w PATH, dodatkowo sprawdza semantykę. rs274 może drukować menu także przy błędach programu, więc kontrolujemy linie spoza menu
i wywołań kanonicznych, obecność PROGRAM_END oraz kod wyjścia procesu. Komunikaty po angielsku (LinuxCNC).

**Ekran** (przycisk „Sprawdź”, lista błędów, klik → linia, ostrzeżenie przy edycji `.ngc`
z `.lnx`) czeka na kopię ekranu QtDragon (sesja 005, Codex) — API jest gotowe.

Ścieżki RIP i G-code są cytowane jako dane powłoki (także apostrofy i spacje).
Proces rs274 zastępuje powłokę przez `exec`, aby limit czasu kończył interpreter.
Testy granicy procesu bez LinuxCNC: `tests/test_interpreter_process.py` (Model-Author: Codex).
