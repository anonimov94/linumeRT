# Współpraca Claude i Codex (v2)

Model-Author: Claude · 2026-10-18. **Jedyne źródło zasad współpracy.** `AGENTS.md` i
`CLAUDE.md` tylko tu odsyłają; sprzeczne zapisy gdzie indziej tracą moc. Zmiana zasad =
osobny commit + wpis w `docs/DECYZJE.md` (sekcja decyzji właściciela). Powód wersji 2: limity tokenów często przerywają
sesje, więc pracujemy małymi krokami, z częstym pushem i jawnym przekazaniem tury.

## Synteza i domknięcie — polecenie właściciela 2026-10-26

Model-Author: Codex. Właściciel polecił dokonać syntezy z Claude i domknąć otwarte gałęzie.
Decyzja Claude z #183 potwierdza HTML/WebGL oraz zamrożenie nowego rozwoju Qt.
Zachowujemy gotowy wspólny backend i istniejącą integrację CAM z #184; po tej porcji
nowe GUI powstaje w kliencie web. Qt pozostaje działającym ekranem awaryjnym.
Poprawka routera klawiatury pola napisu jest częścią domknięcia działania tego ekranu.
Nie deklarujemy wzajemnego przeglądu bez oceny konkretnego SHA. Aktualne ustalenia,
kontrakty i granice odbioru: [synteza](SYNTEZA_MODELI_2026-10-26.md).

## Lekcja projektu — pilnowanie założeń i kolejności (2026-10-24, z aktualizacją powyżej)

Model-Author: Codex. Polecenie właściciela po porównaniu projektu z pierwotnym planem.
Rozwijanie skórek, renderera i ISO równolegle z niedomkniętymi wcześniejszymi etapami
rozproszyło pracę. Wiele działających części nie dało kolejnych odebranych kamieni.
Zachowujemy wykonany kod i przywracamy dyscyplinę domykania planu.

1. **Na początku każdej sesji wróć do celu i kontraktu `CLAUDE.md` oraz rejestru
   `docs/roadmap/plan.json`.** Przed implementacją podaj: ID pierwotnej sesji,
   kryterium/bramkę do zamknięcia, otwarte zależności i jeden mały rezultat tej sesji.
   Sprawdź dotychczasowe dowody, aby nie implementować ponownie ukończonych części.
2. **Pracuj według M0 → M1 → M2/G2 → M3/G3 → M4/G4 → M5/G5 → M6/G6.**
   Domykaj najwcześniejszy otwarty zakres i jego kryteria przed rozwijaniem kolejnego
   kamienia. Wcześniejszy krok zależności lub naprawę blokera ogranicz do zakresu
   niezbędnego do odbioru; zapisz powiązanie i uzasadnienie w rejestrze/dzienniku.
   Przy zewnętrznej blokadzie wykonuj pozostałe dostępne zadania tego etapu;
   nie zastępuj brakującego odbioru deklaracją ani nowym prototypem.
3. **Najpierw doprowadź rozpoczętą funkcję do użytecznego i odebranego działania.**
   Zachowaj GUI od pierwszego kroku (D36), domknij integrację, testy i dokumentację.
   Liczba testów, ukończony backend, zrzut lub podgląd nie zastępują kryteriów całej
   sesji. Wynik automatyczny, pulpit, RT i sprzęt zachowują osobne dowody odbioru.
4. **Nowe pomysły wpisuj jako rozszerzenia pierwotnych sesji w rejestrze.** Sam wpis
   nie zmienia priorytetu, nie otwiera osobnej roadmapy i nie uzasadnia pracy poza
   bieżącym etapem. Rozwijaj wspólną logikę raz; kolejne skórki korzystają z jej
   kontraktu zamiast tworzyć oddzielne implementacje sterowania.
5. **Jawne nowe polecenie właściciela może zmienić zakres lub kolejność.** Wykonaj je
   i zapisz powód, wpływ na wcześniejsze bramki oraz nowe powiązania w `DECYZJE.md`
   i rejestrze. Nie interpretuj ogólnego „kontynuuj” ani dawnych zleceń „wybieraj
   najłatwiejsze tematy” jako zmiany tej kolejności. Rutynowe decyzje w zatwierdzonym
   zakresie podejmuj samodzielnie; ta reguła nie tworzy dodatkowej procedury zgód.
6. **Na końcu sesji rozlicz postęp względem planu:** które kryterium domknięto,
   co nadal pozostaje i jakie jest następne zadanie z tej samej kolejności.
   Aktualizuj wyłącznie rejestr i generuj widoki; nie twórz konkurencyjnej listy statusów.

Wnioski z audytu 2026-10-24: odbiór podstawy obejmuje OD-01, PLAN-27,
LEGACY-RUNTIME i domknięcie rozpoczętego edytora; następnie zaległość 007 oraz M2/G2,
a dalej M3/G3, M4/G4, M5/G5 i M6/G6. Aktualny stan tych zadań pozostaje wyłącznie
w rejestrze; ta lista wyjaśnia powrót do planu i nie jest osobnym harmonogramem.

## Aktualizacja właściciela — wspólna roadmapa 2026-10-24 (ma pierwszeństwo)

Jedyne źródło statusów, powiązań zadań i pozostałego zakresu to `docs/roadmap/plan.json`.
Pierwotne 001–084 i M0–M6 pozostają; późniejsze plany są rozszerzeniami przypisanymi
przez `parents` do tych sesji. Specyfikacje/prompt opisują wymagania, dziennik i raporty
zachowują dowody, `NASTEPNA_SESJA.md` służy przekazaniu oraz środowisku.
Po każdym kroku aktualizuj właściwy rekord i generuj widoki `python3 tools/roadmap.py`.
Nie dopisuj ręcznie do DONE ani tabel statusów w starych planach; `make lint` pilnuje zgodności.
Wybór pracy: najniższa nieukończona sesja z uwzględnieniem rozszerzeń i zależności,
chyba że bieżące polecenie właściciela wskazuje inny zakres. Ukończona część ani
rozszerzenie nie zamykają całej sesji, bramki lub odbioru sprzętu.
Polecenie to zastępuje starsze instrukcje dopisywania do DONE i prowadzenia osobnych planów.
Model-Author: Codex.

## Aktualizacja właściciela — bieżące zlecenie 2026-10-20 (ma pierwszeństwo)

Codex kontynuuje HMI w osobnym checkoutcie i nie zakłada globalnej blokady `prompts/LOCK`
ani nie zajmuje tury blokującej Claude. Claude może niezależnie kontynuować swój zakres.
Ukończone zmiany po autokontroli i zielonych testach autor od razu scala przez PR do `main`
(merge commit, bez przepisywania historii); przegląd drugiego modelu nie jest warunkiem scalenia.
Nie omijamy wymaganych kontroli GitHub. Nie przerywamy cudzych procesów: używamy osobnego
środowiska LinuxCNC/budowy; blokady zasobów dotyczą tylko faktycznie współdzielonej instancji.
Poniższe historyczne zasady tur i oczekiwania na przegląd nie ograniczają tego polecenia.
Model-Author: Codex.

## 1. Tury (na zmianę; wyjątek równoległy: §2a, D28)
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
- D36: GUI od pierwszego kroku — obowiązuje `CLAUDE.md` §11 i
  [`SAVOIR_VIVRE_AI.md`](SAVOIR_VIVRE_AI.md). Funkcja operatora od razu trafia do widocznego,
  użytecznego widoku; kolejne przetestowane porcje (najwyżej około 200 nowych linii) są wypychane.
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
Polecenia i stan środowiska: `docs/NASTEPNA_SESJA.md` §4 (nie duplikuj ich tutaj).

## 7. Podział pracy (roboczy, właściciel może korygować)
**Od 2026-10-18 (D31): cały zakres, łącznie z obszarem Codexa poniżej, prowadzi Claude** (lokalnie,
laptop właściciela). Wyjątek (D32): **HMI według kolejności pracy (`docs/design/HMI_WORKFLOW.md`, etapy
HMI-01…06) prowadzi Codex**, w wolnej chwili; Claude go nie dubluje. Opis niżej zostaje jako podział na wypadek
pełnego powrotu Codexa.
Modele: Claude (Sonnet 5.5 i Opus 5.5) — początkowo w chmurze, od D31 lokalnie na laptopie właściciela
(EndeavourOS, podman, LinuxCNC RIP w kontenerze Debian 12). Codex = astra low, komputer właściciela
(Windows, WSL, VNC, LinuxCNC), niski poziom rozumowania.
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
