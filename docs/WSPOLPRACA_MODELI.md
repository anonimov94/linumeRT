# Współpraca Claude i Codex (v2)

Model-Author: Claude · 2026-10-18. **Jedyne źródło zasad współpracy.** `AGENTS.md` i
`CLAUDE.md` tylko tu odsyłają; sprzeczne zapisy gdzie indziej tracą moc. Zmiana zasad =
osobny commit + wpis w `docs/DECYZJE.md`. Powód wersji 2: limity tokenów często przerywają
sesje, więc pracujemy małymi krokami, z częstym pushem i jawnym przekazaniem tury.

## 1. Tury (na zmianę; wyjątek równoległy: §2a)
- Na górze `docs/NASTEPNA_SESJA.md` jest stała linia:
  `Tura: Claude|Codex · od <UTC> · stan: w toku|oddana`.
- Start: przeczytaj tę linię, `prompts/LOCK` i otwarte PR. Tura drugiego modelu „w toku"
  z ostatnim pushem starszym niż 2 h = przerwana (limit): zapisz to w dzienniku i przejmij.
  Świeżej tury nie przejmuj.
- Koniec albo zbliżający się limit: commit, push, `stan: oddana`, zwolnij LOCK.
- Przekazanie wyłącznie w plikach: sekcje „Dla Codex:" i „Dla Claude:" w
  `NASTEPNA_SESJA.md`; odpowiedź w tym samym pliku. Czat właściciela nie jest kanałem.

## 2. Blokada `prompts/LOCK`
Jedna linia: `<model> · sesja NNN · <UTC> · <opis>`. Brak pliku lub pusty = wolne.
Zakładasz na starcie, zwalniasz przy oddaniu (osobny commit `lock: zwolniony`).
Cudzego świeżego locka nie ruszaj; przerwany (>2 h bez pushu) przejmij wpisem w dzienniku.

## 2a. Blokady zasobów (rzadka praca równoległa, D30)
Tury (§1) wystarczają, gdy modele pracują na zmianę. Gdy właściciel wyjątkowo uruchomi oba naraz,
współdzielone zasoby chroni `tools/lock.py` (blokada w `state/locks/`, atomowa, TTL 2 h):
- zasoby: `linuxcnc` (instancja LinuxCNC/RIP, port VNC i DISPLAY), `wsl-build` (wspólny katalog budowy);
- przed użyciem: `python tools/lock.py acquire <zasób> --model Claude|Codex --note "..."`;
  zajęte (kod 1) = nie czekaj w pętli, zrób inny krok albo zapisz to w „Stan zatrzymania";
- po użyciu: `release`; przerwaną blokadę (>TTL) wolno przejąć, zapisz to w dzienniku;
- pliki w repo (kod, dokumenty) chronią osobne gałęzie i checkouty (D28), nie blokady.

## 3. Małe kroki i częsty push
- Krok = jedna spójna zmiana, zwykle ≤ 5 plików lub ≈ 200 linii. Po każdym kroku:
  lint i szybkie testy → commit → push. Niczego nie kumuluj lokalnie.
- Draft PR otwieraj po pierwszym kroku, nie na końcu sesji.
- Przed długą operacją (budowa, duże testy, klonowanie) wypchnij wszystko.
- Po każdym pushu dopisz jedną linię w sekcji „Stan zatrzymania" w `NASTEPNA_SESJA.md`
  (zrobione / następny krok). To tanie, a ratuje przerwaną sesję.
- Praca nieukończona żyje na gałęzi z draft PR, nigdy tylko lokalnie.

## 4. Oszczędność tokenów
- Czytaj tylko potrzebne: `git diff --stat`, `grep -n`, zakresy linii, `| tail -20`.
  Nie wypisuj całych plików ani logów; nie powtarzaj odczytów.
- GitHub przez `gh api ... --jq`, klony płytkie (`--depth 1`), bez subagentów,
  chyba że właściciel o nie poprosi.
- Pisz zwięźle: wpis w dzienniku ≤ 10 linii, raporty w plikach, w czacie 3–5 zdań.
- Zadanie, które nie mieści się w jednym kroku, podziel i zapisz podział w `NASTEPNA_SESJA.md`.

## 5. Etapy, przegląd i scalanie (D26)
- Etap = jedna sesja z planu (NNN) albo jej wyraźnie wydzielona część, spełniająca kryteria
  akceptacji i Definition of Done (`CLAUDE.md` §11). `main` zawiera wyłącznie ukończone
  etapy: zielone testy, dokumentacja, wpis w dzienniku, brak niedokończonego kodu.
- Praca w toku żyje na gałęzi i w draft PR (§3). Na koniec etapu PR przestaje być draftem
  i jest scalany. PR nie wisi: najpóźniej w następnej turze drugi model albo go scala, albo
  wypisuje konkretne usterki, a autor poprawia i scala. PR bez ruchu przez 2 tury dzielimy
  na mniejsze albo zamykamy z notatką w `NASTEPNA_SESJA.md`.
- Scalać mogą oboje modele (decyzja właściciela 2026-10-18), po zielonych kontrolach,
  merge commit, bez przepisywania historii `main`.
- Przebieg: autor kończy etap i oznacza PR jako gotowy. (a) Drugi model dostępny: przegląd
  komentarzem (model, SHA, wynik), potem scala albo zwraca. (b) Niedostępny lub limit (D25):
  autor scala po autokontroli i pisze w PR „autokontrola, bez niezależnego przeglądu";
  drugi model robi przegląd wsteczny po powrocie (SHA scalenia).
- Zmiany wyłącznie w `docs/` autor scala od razu, z adnotacją w PR.
- Commity, PR i dziennik: `Model-Author: Claude` albo `Model-Author: Codex`. Nie przypisuj
  sobie cudzej pracy. Nie nazywaj autokontroli niezależnym przeglądem.

## 6. Środowisko testowe
Polecenia i stan środowiska: `docs/NASTEPNA_SESJA.md` (nie duplikuj ich tutaj).

## 7. Podział pracy (roboczy, właściciel może korygować)
**Od 2026-10-18 (D31): cały zakres, łącznie z obszarem Codexa poniżej, prowadzi Claude** (lokalnie,
laptop właściciela). Opis niżej zostaje jako podział na wypadek powrotu Codexa.
Modele: Claude = Sonnet 5.5, działa w chmurze, bez dostępu do WSL właściciela. Codex = astra
low, działa na komputerze właściciela (Windows, WSL, VNC, LinuxCNC), niski poziom rozumowania.
Obszaru drugiego modelu nie ruszamy bez wpisu w `NASTEPNA_SESJA.md`. Różnice uzupełniamy:
- **Claude:** projekt i specyfikacje (architektura, kontrakty, model Plant, protokół LRT-NET),
  logika wielokrokowa i generatory cykli, refaktory przekrojowe, wymagania REQ i macierz
  pokrycia, decyzje, IP i licencje, rozbijanie sesji na kroki, niezależny przegląd PR Codex.
- **Codex:** wszystko, co trzeba uruchomić w WSL/Windows/VNC: budowa i testy LinuxCNC,
  konfiguracje HAL/INI, skrypty PowerShell/bash, workflow CI, testy integracyjne i zrzuty,
  mechaniczna implementacja według gotowej specyfikacji, poprawki po wynikach testów.
- **Claude → Codex:** w „Dla Codex:" krótka, jednoznaczna specyfikacja: pliki, kryteria
  akceptacji, polecenie testu. **Codex → Claude:** w „Dla Claude:" ogon wyników/logów,
  pytania projektowe, co zablokowało.
- Spór o kompetencje rozstrzyga właściciel; do tego czasu obszar ma autor pierwszego commita w nim.
