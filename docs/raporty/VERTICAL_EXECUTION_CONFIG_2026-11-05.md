# Konfiguracja wykonawcza ze zweryfikowanego zadania

Model-Author: Codex · 2026-11-05. Pierwsza porcja poziomu3, nie odbiór wykonania.

`linumert run-config JOB --verification RAPORT.json --target sim|plant --out NOWY_KATALOG`
generuje samodzielne wejścia LinuxCNC i Plant z tego samego zweryfikowanego pakietu.
API/WebHMI pozwala pobrać ich ZIP po dodatnim verify. Nie uruchamia procesów, nie łączy
CNC, nie resetuje E-STOP/STO i nie zezwala na ruch. Werdykt offline nie jest autoryzacją
wykonania; manifest konfiguracji ma status configured i execution_authorization=false.

## Wiązanie danych

Raport weryfikacji ma poprawny digest, właściwy job_id, verified oraz wszystkie wymagane
kontrole passed. Założony początek/T0/G92=0 i ustawienie detalu są zachowane, nie udawane
jako odczyt kontrolera. API odczytuje wyłącznie raport zapisany przez skonfigurowaną bramę,
pod podanym identyfikatorem; klient nie przesyła własnego raportu ani ścieżki pliku.

Każdy napęd otrzymuje własną pochodną zamrożonego szablonu. Zmienia się wyłącznie jego
techniczne id w osobnej bibliotece drive_library; wszystkie parametry pozostają identyczne
z drives.json. Nie czytamy bieżącej biblioteki ani nowych wartości domyślnych. Ten sam
rachunek counts_per_unit zasila LinuxCNC i model Plant. Pełny oryginalny pakiet pozostaje
w job/, raport w verification.json; tabela tool.tbl i program są identyczne bajtowo.
Plik parametrów inicjalizuje zapisany układ detalu i wyzerowany G92.

execution.json wiąże wszystkie zasoby SHA-256, job_id, verification_id, skale i mapę
pochodnych szablonów. Odczyt sprawdza także ponowne wygenerowanie całości: samo podpisanie
nowego hasha ręcznie zmienionego HAL nie wystarcza. Publikacja nowego katalogu jest atomowa
i odmawia nadpisania istniejącego. Ścieżki zasobów nie mogą wychodzić poza pakiet.

Eksport obsługuje wyłącznie sim/Plant, lokalne połączenie Plant i domyślnie zachowuje
HMI_ESTOP_BYPASS=0. CLI wymaga jawnego --test-mode dla testowego bypassu; API nie przyjmuje
tego pola. Oryginalny model jest zachowany, pochodny cel symulacyjny nie ma konfiguracji
połączenia sprzętowego. Nie jest to zmiana zasad bezpieczeństwa.

## Checkpoint

37 testów eksportu/werdyktu/architektury/konfiguracji PASS; następnie65 regresji CLI,
przygotowania i API PASS (zakresy częściowo wspólne). ZIP API zgodny z backendem, token/Host
i pola payloadu sprawdzone, brak zmiany stanu fake CNC i oryginalnego pakietu.
Dwa rzeczywiste testy rs274 PASS: sim i Plant konsumują wyeksportowane narzędzia/parametry/
INI/remap i odtwarzają ten sam zweryfikowany tor. To test interpretera offline, nie start
kontrolera ani wykonanie programu w Plant. Lint całego drzewa PASS.

Pozostają kliknięty odbiór pobrania WebHMI, pełna regresja, końcowe CI i scalenie tej porcji.
Dalszy poziom3: prywatna robocza kopia konfiguracji (LinuxCNC zapisuje .var/logi), start
instancji, sprawdzenie jej konfiguracji/tabeli/początku/T0 i istniejących blokad gotowości,
następnie jawny Start oraz telemetria, pauza/wznowienie/Stop/awarie. Kontrola eksportu nie
udaje wykonania tych kroków. Poziom4 — raport porównawczy — pozostaje otwarty.
NIEZWERYFIKOWANE NA SPRZĘCIE.
