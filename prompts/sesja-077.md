# Sesja 077/084 · M6 Wtyczki, instalator, alfa · Instalator dla Debiana 12 + LinuxCNC 2.9

Kolejność: sesja 77 z 84 · poprzednia: sesja-076. Sesje uruchamia harmonogram po odnowieniu limitów konta — daty nie są stałe.

Jesteś agentem-programistą projektu **linumeRT** (otwarty ekran operatora i narzędzia dla LinuxCNC, ekran na bazie QtDragon, maszyny CNC DIY). Pracujesz samodzielnie, bez użytkownika przy klawiaturze i bez fizycznej maszyny (do testów służy wirtualna maszyna Plant).

## Zanim zaczniesz
1. Przeczytaj `CLAUDE.md` (kontrakt — ma pierwszeństwo przed tym promptem) i `docs/DECYZJE.md`.
2. Przeczytaj 3 ostatnie wpisy w `docs/DZIENNIK.md` i sprawdź `git log -10`.
3. Jeśli czegoś z wcześniejszych sesji brakuje, zrób minimum potrzebne do tej sesji i zapisz to w dzienniku.
4. Jeśli istnieje gałąź `wip/sesja-077` — to przerwana wcześniejsza próba tej sesji: zacznij od niej i kontynuuj.
5. Po każdym ukończonym punkcie zakresu: commit i push na `wip/sesja-077` (limit konta może przerwać pracę w dowolnej chwili).

## Cel kamienia M6
Wtyczki deklaratywne, instalator dla Debiana 12 + LinuxCNC 2.9, dokumentacja, przegląd IP przed wydaniem, regresja na Plant, wydanie alfa.

## Cel tej sesji
packaging/install.sh.

## Zakres pracy
1. Sprawdzenie systemu, venv /opt/linumert, instalacja ekranu do ścieżki QtVCP, halcompile komponentów, przykładowe konfiguracje, bez nadpisywania konfiguracji użytkownika.
2. update.sh z kopią i rollbackiem, uninstall.sh, MANIFEST.json.
3. Test idempotencji w kontenerze Debian 12.
4. **Obraz live USB / ISO do instalacji (polecenie właściciela, 2026-10-19)**: Debian 12 + jądro PREEMPT_RT +
   LinuxCNC 2.9 (pakiety linuxcnc.org) + linumeRT z `install.sh`, budowany `live-build` w GitHub Actions
   (job ręczny i przy tagu wydania). Tryb live (próba bez instalacji, symulator + Plant od razu) i instalator
   na dysk komputera maszyny. Wynik: `linumert-<wersja>-amd64.iso` jako artefakt / zasób wydania
   (limit 2 GB na plik — w razie potrzeby obraz bez dokumentacji i z kompresją xz), suma SHA-256,
   instrukcja wypalenia (`dd`, Etcher / Ventoy). Po pierwszym starcie: test latencji (`latency-histogram`)
   i ostrzeżenie, gdy komputer nie nadaje się do RT. Laptop dewelopera (EndeavourOS) bez zmian:
   tam instalatorem jest `tools/linumert-start.sh` (podman).

## Kryteria akceptacji
- [ ] ISO startuje w QEMU (BIOS i UEFI) do pulpitu z ekranem linumeRT na symulatorze; instalator kończy się na dysku wirtualnym
- [ ] dwukrotna instalacja nie psuje
- [ ] `make lint test` przechodzi (oraz `make test-c` / `make test-linuxcnc`, jeśli dotyczy i są dostępne)
- [ ] `tests/test_ip_guard.py` przechodzi; nowe zasoby w `docs/PROVENANCE.md`
- [ ] nowe zależności wpisane do `docs/LICENCJE.md`

## Zakończenie sesji
1. Dopisz wpis do `docs/DZIENNIK.md`: `## 077 — Instalator dla Debiana 12 + LinuxCNC 2.9` z polami: zrobione, decyzje, do sprawdzenia ręcznie, długi.
2. Dopisz linię `077 | <data> | <krótki opis>` do `prompts/DONE.md`.
3. Scal `wip/sesja-077` do `main` (commit z prefiksem `sesja 077:`), wypchnij `main`, usuń gałąź wip.
4. Na końcu odpowiedzi podsumuj po polsku w 5–8 punktach: co powstało i co użytkownik powinien sprawdzić.
