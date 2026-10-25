# Jedna roadmapa linumeRT

Model-Author: Codex · 2026-10-24. Na polecenie właściciela.

Jedynym źródłem **statusów, powiązań zadań i pozostałego zakresu** jest
[plan.json](plan.json). Zachowuje pierwotne sesje 001–084 i kamienie M0–M6
z commita `796c6a2`. Prompty sesji i specyfikacje opisują szczegółowe wymagania;
kontrakt, decyzje i wymagania REQ nadal mają swoje dotychczasowe pierwszeństwo.
Rejestr nie zmienia zasad współpracy z `docs/WSPOLPRACA_MODELI.md`.

Późniejsze HMI-01…06, D38, plan 21–27, SKIN-00…06, ISO, konkursy oraz
prace edytora są rozszerzeniami przypisanymi przez `parents` do sesji pierwotnych.
Dawne numery 085–088 i oznaczenia konkursowe zachowano jako aliasy lub ID.
Nie otwierają drugiego harmonogramu i nie zwiększają mianownika 84.
Historyczne PR narzędzi/diagnostyki i symulacji są postępem istniejących sesji;
nie każda poprawka musi tworzyć nowe zadanie.

## Aktualizacja

1. Przed pracą sprawdź rejestr i otwarte PR; wybierz najniższą nieukończoną sesję
   oraz jej rozszerzenia/zależności, chyba że bieżące polecenie właściciela wskazuje inny zakres.
2. Edytuj wyłącznie właściwy rekord w `plan.json`: `status`, `progress`,
   `remaining`, `evidence` oraz datę `updated`. Nowy zakres otrzymuje unikalne ID,
   sesje nadrzędne i odsyłacz do specyfikacji/promptu. Numeracji 001–084 nie zmieniaj.
3. `done` oznacza ukończony zakres danego rekordu z dowodami. `partial` oznacza
   działającą część i otwarte kryteria, `in_progress` aktywną pracę, `acceptance`
   oczekiwanie na odbiór, `planned` brak potwierdzonej realizacji, a `blocked`
   jawną blokadę z przyczyną i warunkiem odblokowania w `remaining`.
   Ukończone rozszerzenie nie zamyka automatycznie sesji nadrzędnej ani bramki.
4. Uruchom `python3 tools/roadmap.py`, a następnie `python3 tools/roadmap.py --check`.
   Generator aktualizuje [pełny plan](PLAN.md), [HTML](index.html),
   [spis promptów](../../prompts/README.md), [DONE](../../prompts/DONE.md)
   oraz [grafikę postępu w README](../raporty/postep-sesji.svg). Grafika liczy wyłącznie pierwotne
   sesje ze statusem `done`; `make lint` wykrywa jej nieaktualność.
   Tabela M0–M6 w głównym README jest generowana między znacznikami
   `MILESTONES:START` / `MILESTONES:END`. Liczy ukończone sesje i rekordy z otwartymi
   kryteriami (sesje oraz powiązane rozszerzenia), bez automatycznego zaliczania bramek.
   Tekst README poza tym blokiem pozostaje redakcyjny; nie usuwaj znaczników.
   Nie edytuj tych widoków ręcznie. HTML działa także lokalnie, bez serwera.
5. Zapisz wyniki, SHA i ograniczenia w raporcie/dzienniku; dodaj odsyłacz w rejestrze.
   `NASTEPNA_SESJA.md` przechowuje przekazanie i środowisko, nie alternatywną listę statusów.
   Dawne plany są specyfikacjami lub historią, a nie samodzielnymi kolejkami.

`make lint` sprawdza zgodność wygenerowanych widoków z rejestrem oraz aktualną
zawartością promptów. Zmiana promptu wymaga ponownego generowania HTML.
Dowodów historycznych nie zastępuj deklaracją nowego testu. Automatyczny PASS,
ręczny odbiór pulpitu, kwalifikacja RT i odbiór fizycznej maszyny są odrębne.
NIEZWERYFIKOWANE NA SPRZĘCIE.

## Korekty przy migracji

Sesje 007 i 048 otrzymały `partial`: dawny rejestr wymieniał odłożone tłumaczenia
Qt oraz podprogramy kieszeni/rowków mimo statusu wykonania. Dawne wpisy zachowano
w `historical_completion`; historię wykonanych prac pozostawiono w Git i dzienniku.
Pozostałe statusy częściowe nie oznaczają ponownego odbioru całego kodu.
Wynik automatyczny P0/G1 pozostaje historycznym PASS; otwarty odbiór stanowiska,
usterka OD-01 i wymagania sprzętowe mają odrębne rekordy. Stan otwartego PR edytora
należy zaktualizować po jego scaleniu, bez zaliczania kodu spoza main.
