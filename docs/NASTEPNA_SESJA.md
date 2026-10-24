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

## Dla Claude: poprawka jednostek LIMITS-PREFLIGHT — 2026-10-24

Model-Author: Codex. Na bazie PR #103 / 98191c4 odtworzyłem pomylenie jednostek:
limit 10 cali był traktowany jak 10 mm, a ruch 5 cali jak 127 mm.
Gałąź `codex/review-limits-units` zawiera przeliczenie granic XYZ do mm oraz regresję.
Zmieniony kod: `core/linumert/programs/limits.py`; nowy test: `tests/test_limits_units.py`.
Weryfikacja Windows/Python 3.12: 31 testów PASS, 4 subtesty PASS, 1 test LinuxCNC
pominięty; ruff dla zmienionego kodu i check_requirements PASS.
Widoki roadmapy wygenerowano z separatorami POSIX (generator używa os.path.relpath).
Pełny odbiór Debian/LinuxCNC pozostaje do wykonania. Proszę włączyć poprawkę przez
PR do Twojej gałęzi przed końcowym odbiorem #103. Nie zmieniałem Twojej gałęzi.
Stan zatrzymania: poprawka i regresja gotowe; następny krok — integracja z #103 i CI.
