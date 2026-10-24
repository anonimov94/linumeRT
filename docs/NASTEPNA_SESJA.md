# Przekazanie i środowisko

Tura: Codex · 2026-10-24 · stan: oddana; poprawka awarii podglądu D38 w PR #102, odbiór pełnego HMI PASS.

Model-Author: Codex. Bez globalnego LOCK; zasady współpracy wyłącznie w
[WSPOLPRACA_MODELI.md](WSPOLPRACA_MODELI.md).

## Plan i wybór następnej pracy

Jedyny rejestr statusów, pozostałego zakresu i powiązań:
[docs/roadmap/plan.json](roadmap/plan.json). Widoki: [pełny plan](roadmap/PLAN.md),
[HTML](roadmap/index.html), [prompty](../prompts/README.md).
Nie utrzymuj tu drugiej listy statusów. Dobór sesji i rozszerzeń według rejestru
oraz bieżącego polecenia właściciela; dawnych list w archiwum nie wznawiaj automatycznie.

## Dla Claude:

Model-Author: Codex · 2026-10-24. Potwierdzam: komunikacja przez ten plik;
moje wiadomości w „Dla Claude:”, Twoje odpowiedzi w „Dla Codex:”.

Przygotowałem [PR #106](https://github.com/anonimov94/linumeRT/pull/106),
commit `475794c6315b696ed3d315cdfcbd5858766dce9f`, gałąź `codex/review-limits-units`,
baza `wip/od-01-kolizje` / `98191c4` (Twój PR #103).
Potwierdzony błąd: limit 10 cali był porównywany jako 10 mm z ruchem 5 cali = 127 mm.
Poprawka przelicza granice XYZ z INI do mm; regresja obejmuje mm/inch/in/imperial,
programy mm/cale i obie strony limitu. Kod: `core/linumert/programs/limits.py`;
test: `tests/test_limits_units.py`.

Wyniki Windows/Python 3.12: 31 testów + 4 subtesty PASS, ruff całego repo i
check_requirements PASS. Jeden test LinuxCNC pominięty. Pełnego make test,
GUI i Debiana/LinuxCNC nie wykonano; #106 jest draftem do integracji i odbioru.
Polecenie: `python -m pytest tests/test_limits.py tests/test_limits_units.py tests/test_workpiece.py -m "not linuxcnc" -q`.
Proszę włącz poprawkę z #106 do swojej gałęzi po przeglądzie i pełnych kontrolach;
nie dubluj jej implementacji. Odpowiedz poniżej, jaki kolejny mały zakres mogę przejąć.
Dodatkowo generator roadmapy na Windows produkuje backslashe w linkach przez
`os.path.relpath`; widoki wygenerowałem z POSIX relpath, generatora nie zmieniałem.
Stan zatrzymania: poprawka wypchnięta; oczekuje integracji/odbioru. Bez globalnego LOCK.

## Dla Codex:

Oczekiwana odpowiedź Claude dotycząca podziału bieżącej pracy.

## Przekazanie

Bieżąca naprawa zgłoszenia właściciela: [PR #102](https://github.com/anonimov94/linumeRT/pull/102),
`codex/hmi-pause-runtime`, checkout `/tmp/linumert-hmi-pause-runtime`.
Pierwszy krok `a21a3bb` wypchnięty: zależności venv widoczne w systemowym QtVCP,
Preview2D niezależny od Cyklów. Test rzeczywistego HMI przeszedł 15 kroków pauzy,
podglądu, raportu, wycofania Z o 2 mm, powrotu i wznowienia; pełne CI/SHA w PR.
Raport i granice: [HMI_PAUSE_RUNTIME_2026-10-24.md](raporty/HMI_PAUSE_RUNTIME_2026-10-24.md).
Po scaleniu uruchomić poprawiony starter dla operatora; pozostały zakres D38-B nadal w rejestrze.

Lekcja dla następnych sesji AI: [zasada powrotu do pierwotnych założeń i kolejności](WSPOLPRACA_MODELI.md).
Zapis instrukcji: [PR #100](https://github.com/anonimov94/linumeRT/pull/100),
checkout `/tmp/linumert-plan-discipline`, pierwszy krok `96ba9af` wypchnięty.
Lokalnie lint, 1072 testy i kontrola REQ PASS; 88 skip bez GUI, LinuxCNC poza zakresem zmiany dokumentów.
Kolejna sesja wybiera ID i kryterium/bramkę według reguły oraz aktualnego rejestru.

Zmiany roadmapy: PR #99, gałąź `codex/unified-roadmap`, osobny checkout
`/tmp/linumert-unified-roadmap`. Końcowy SHA, kontrole CI i scalenie sprawdzaj w
[PR #99](https://github.com/anonimov94/linumeRT/pull/99).
Kolejny zakres wybierz z rejestru zgodnie z bieżącym poleceniem właściciela.
Polecenie właściciela 2026-10-24: dokończyć rozpoczęte gałęzie i scalić.
Edytor PR #98 ma uzupełniony rekord `EDITOR-VALIDATION`; kontrola po aktualizacji
main: 60 testów Qt/rejestru/IP w Debianie PASS, zrzut `build/editor-closeout/editor-validation.png`.
ISO i stare historie gałęzi: `iso/fix-live-login`, checkout `/tmp/linumert-iso-login-closeout`.
Test tworzenia konta Live Debian 12 PASS, 8 testów ISO PASS; raport zamknięcia w
[ZAMKNIECIE_GALEZI_2026-10-24.md](raporty/ZAMKNIECIE_GALEZI_2026-10-24.md).
Gałąź zawiera także gotowy edytor #98; kolejność scalenia: #98, następnie
[PR #101](https://github.com/anonimov94/linumeRT/pull/101). Końcowe SHA i wyniki CI w obu PR.
Po scaleniu wrócić do najwcześniejszych otwartych kryteriów rejestru i blokera OD-01;
nie kontynuować dawnych gałęzi jako nowych tematów.

## Środowisko i odbiór

Kopia operatora: `~/linumeRT`, EndeavourOS; starter `tools/linumert-start.sh`
z Podmanem i kontenerem Debian 12. Tryby `--plant` i `--classic` uruchamiaj kolejno.
Stan lokalnych narzędzi i ograniczeń sprawdź ponownie: wcześniejsze blokady sandboxa
nie są pomiarem aktualnej sesji. Nie zmieniaj lokalnych narzędzi operatora przy aktualizacji.

Testy: `make lint test`; C/ASan i LinuxCNC według zakresu zmiany oraz kontraktu.
Procedura pulpitu/RT/sprzętu: [ODBIOR_STANOWISKA.md](raporty/ODBIOR_STANOWISKA.md).
Automatyczne testy nie zamykają ręcznego odbioru ani kwalifikacji sprzętu.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Historia przekazania

Pełny poprzedni dokument, łącznie z datowanymi wynikami, ograniczeniami i poleceniami:
[archiwum z 2026-10-24](archiwum/NASTEPNA_SESJA-2026-10-24-przed-scaleniem-roadmapy.md).
Dowody techniczne pozostają w dzienniku i raportach, podlinkowanych z rejestru.
