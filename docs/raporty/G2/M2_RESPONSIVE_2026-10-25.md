# M2 / 028 — dopasowanie kart do szerokości ekranu

Model-Author: Codex · 2026-10-25 · PR #161.

Karty Start i Narzędzia używają wspólnego układu: obok siebie przy dostatecznej
szerokości, pod sobą poniżej 1100 px obszaru strony lub gdy ich minima nie mieszczą
się obok siebie. Checklistę można zawijać; tabela i formularz zachowują własne
przewijanie. Przestawienie istniejących widgetów zachowuje niezapisane wartości i fokus.
Bez nowych zależności, zmian ACTION, HAL, trybów lub zezwoleń ruchu.

## Dowody

Źródła kodu: f76554f. Debian 12, istniejący Python 3.11/venv i PyQt5, offscreen.
- 15 testów układu, złożenia HMI i narzędzi PASS.
- Pełna powłoka ze stylem: Start/Narzędzia przy 1280→1920→1280, brak poziomego
  przewijania strony; nawigacja bez ACTION. Wpis opisu i Tab do oprawki PASS.
- Osobne karty 800→1600→800: zmiana wierszy/kolumn, zachowanie szkicu i fokusu PASS.
- Istniejący test STL: samodzielne okno 1200×600, brak poziomego przewijania edytora,
  etykieta nie nachodzi na pole, przycisk Zapisz osiągalny przez przewijanie PASS.
- Strażnik IP: 10 PASS po odtworzeniu dowiązań przez git archive.
- [Start 1280×768](M2_RESPONSIVE_start.png), [Narzędzia 1280×768](M2_RESPONSIVE_tools.png).
  Surowe zrzuty rzeczywistego Qt z atrapami CNC; długie komunikaty to dane testu.

## Granice odbioru

Lokalne uruchomienie LinuxCNC niewykonane: po przygotowaniu środowiska wspólna
lease zajęta przez Claude (`wyglad`). Nie przejmowano zasobów ani nie zatrzymywano
procesów. Wcześniejsze nieudane starty helpera nie uruchomiły LinuxCNC, a obie
własne lease zostały zwolnione. CI właściwego kodu pozostaje do rozliczenia.

Pierwszy pełny zestaw lokalny rozpoczęto z kopii NTFS, przed odtworzeniem
dowiązań przez git archive; wyników błędów tej kopii nie traktujemy jako odbioru
źródeł. Docelowy wynik pełnych kontroli należy odczytać z CI PR #161.

To ukończona porcja układu. Sesja 028 pozostaje partial; odbiór pozostałych
podstron i skórek, stanowiska i sprzętu pozostaje otwarty. Autokontrola autora,
bez niezależnego przeglądu. NIEZWERYFIKOWANE NA SPRZĘCIE.

## Uzupełnienie i przekazanie testów właściciela

Po zwolnieniu zasobów wykonano próbę LinuxCNC f76554f: FAIL, 69,92 s.
Pierwszy błąd: timeout 02_estop_zwolniony, następnie 22 błędy wynikające z aktywnego
E-STOP. Bez diagnozy przyczyny i bez uznania odbioru. Obie lease zwolnione.
Właściciel przekazał dalszy odbiór Claude na laptopie EndeavourOS. Rozpoczęty
pełny zestaw lokalny przerwano SIGINT na polecenie właściciela; nie jest PASS.
Zakres dla Claude: układ/fokus przy 1280×768, STL 1200×600, pełny samotest QtVCP
oraz porównanie timeoutu E-STOP z main. Nie zmieniać blokad HAL dla zaliczenia testu.
