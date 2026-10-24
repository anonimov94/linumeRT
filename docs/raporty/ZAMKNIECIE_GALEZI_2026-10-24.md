# Zamknięcie rozpoczętych gałęzi — 2026-10-24

Model-Author: Codex. Polecenie właściciela: dokończyć wszystkie gałęzie i scalić.
Zakres: istniejący edytor (044/047), poprawka konta Live ISO (077) i historia starych gałęzi.
Pozostałe niezakończone funkcje roadmapy nie są uruchamiane tym poleceniem.

## Gałęzie lokalne z poprawkami już obecnymi w main

Dla każdej gałęzi `git cherry main <gałąź>` wykazał wyłącznie `-`: wszystkie poprawki
commitów bez scalania mają odpowiedniki w main. Dodatkowa kontrola scalenia numeric
wykazała usunięcie trzech znaczników konfliktu dziennika i zachowanie wpisów obu stron;
bez dodatkowej zmiany kodu.

| Gałąź | Zachowany HEAD |
|---|---|
| `codex/bounded-offline-interpreter` | `6f06ab08a4913334dbad6bb66f39b9832efa21e7` |
| `codex/numeric-keyboard-entry` | `c665e2535ffb76f57fbe71a7ab60cf5bdb348ce4` |
| `codex/plan-21-27-refinement` | `c58cd474153622586a5225728e8df377fb1dc654` |
| `codex/plant-hmi-toolchange` | `d83f3639428e153f903d685e2b75fbcfb2ec023d` |
| `codex/status-endeavouros` | `2d4967e4daa4730f93aa2825e48cbf677484a240` |

Scalenie historii strategią `ours` zastosowano wyłącznie do powyższych sprawdzonych
odpowiedników. Nie odtwarzano starych wersji kodu i statusów dokumentacji.
Drzewo przed/po scaleniu historii jest identyczne: `7bad334348d2ab36efe7b51ada8656406329709a`.
Katalogi robocze i dane użytkownika pozostają zachowane.

## Nowe zmiany i odbiór

Edytor: PR #98 — walidacja niezapisanej treści, przejście do błędu, wyszukiwanie
i zamiana z Undo; integracja z aktualnym rejestrem wykonana, 60 testów Qt/rejestru/IP w Debianie PASS.
Końcowe kontrole po synchronizacji są w PR #98.

ISO: poprawka konta `linumert`, zależności user-setup/sudo, jawny autologin LightDM
oraz test tworzenia konta Live w Debianie 12 (PASS); budowa obrazu w kontrolach PR #101.
Publikacja trwałego wydania nadal tylko z ręcznego workflow_dispatch (D39).

Końcowe SHA, wyniki i numery PR są zapisywane w PR i rejestrze roadmapy.
Odbiór pulpitu, start rzeczywistego obrazu i sprzęt pozostają odrębnymi zadaniami.
