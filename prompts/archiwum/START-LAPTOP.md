# Prompt startowy: sesja Claude na laptopie (terminal)

Model-Author: Claude · 2026-10-18. Wklej jako pierwszy prompt w katalogu repo na laptopie.

```
Pracujesz nad linumeRT jako Claude, lokalnie (EndeavourOS), w osobnym checkoucie; Codex może działać obok.
Start (czytaj oszczędnie): CLAUDE.md, docs/WSPOLPRACA_MODELI.md, docs/NASTEPNA_SESJA.md ("Stan main",
"Dla Codex"), prompts/LOCK, otwarte PR (gh api repos/anonimov94/linumeRT/pulls).
Przed użyciem LinuxCNC: python tools/lock.py acquire linuxcnc --model Claude --note "<opis>"
(jeśli tools/lock.py brak, PR #20 niescalony: linia w prompts/LOCK); po pracy release.

Środowisko: tools/dev/debian-container.sh <polecenie> (Debian 12, D27; nic nie instaluj w Archu).

Zadania (małe kroki, commit i push po każdym):
A. tools/dev/debian-container.sh make lint test test-c test-san  — zapisz wynik. Poprzednio w chmurze:
   432 pytest OK, testy C 29/59/20 OK, ASan/UBSan bez usterek (do potwierdzenia na Debianie 12).
B. Przegląd wsteczny PR #13–#17 (scalone przez właściciela bez przeglądu): NASTEPNA_SESJA, "Dla Codex" pkt 0
   i "Zlecenia po sesji 015" (drive.c: establish_offset, homing_update, krokowiec; machine.c: drive_inputs,
   switch.S.drive; homing_master.py; PR #17: python -m linumert_plant serve ... --lockstep i
   plant/server/test_master.py --axes 4 --distance 50000, oczekiwane: utracone 0, spóźnione 0).
   Wynik jako komentarz w PR: model, SHA, wynik. Kod zmieniaj tylko przy uzasadnionej usterce.
C. Jeśli jest LinuxCNC RIP: pytest -o addopts= -m linuxcnc tests/test_hal_comps.py. Budowa LinuxCNC (PR #3,
   sesja 003) to zakres Codexa — nie wchodź mu w drogę.

Zasady: Model-Author: Claude w commitach/PR/dzienniku; własnych PR-ów (#18, #19, #20) nie scalasz;
oszczędzaj tokeny (bez całych plików i logów, raport 3-5 zdań). Na końcu: wpis w docs/DZIENNIK.md (<=10 linii),
"Stan zatrzymania" i linia "Tura:" w NASTEPNA_SESJA.md, zwolnij blokadę/LOCK, push.
```
