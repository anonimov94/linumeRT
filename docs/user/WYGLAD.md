# Wygląd HMI: palety i własne kolory

Model-Author: Claude · 2026-10-25 · M2 (028). NIEZWERYFIKOWANE NA SPRZĘCIE.

W ekranie operatora (szyna po lewej) jest obszar **Wygląd**. Zmienia wyłącznie kolory; układ,
rozmiary i fonty zostają. Zmiana wyglądu **nie wysyła żadnych poleceń do maszyny**.

- **Paleta:** Classic Turquoise (domyślna), Graphite Gray, Reactor Green, Ion Blue, Neon Punk.
- **Własne kolory:** dziesięć ról (tło, panele, przyciski, tekst, tekst pomocniczy, akcent,
  ostrzeżenie, błąd / E-STOP, sukces, informacja). Kolor wybierasz próbnikiem albo wpisujesz `#rrggbb`.
  Pozostałe odcienie (linie, tła stanów) są liczone automatycznie.
- **Zastosuj (podgląd):** zmienia ekran od razu. **Zapisz:** zachowuje po restarcie
  (`~/.config/linumert/appearance.json`, albo plik z `LINUMERT_APPEARANCE`). **Przywróć domyślne:**
  kasuje zapis i wraca do Classic Turquoise.
- **Ochrona czytelności:** ustawień nie da się zastosować ani zapisać, gdy tekst lub znaczniki stanu mają
  za mały kontrast (WCAG: 4,5:1 tekst i błąd, 3:1 pozostałe, na tle i na panelu), tło nie różni się od
  paneli albo kolor błędu przestaje być czerwony, sukcesu zielony, a ostrzeżenia bursztynowy.
  Przyczyna jest podana pod polami. Uszkodzony plik zapisu jest ignorowany (wraca domyślny wygląd).
- **Ograniczenie:** widoki rysowane własnym kodem (symulacja 3D, ścieżka) przejmują kolory po ponownym
  uruchomieniu ekranu. Zmiana układu paneli i kształtu przycisków (prawdziwe skórki) to osobny etap.


## Widok HMI (rodzina)

Model-Author: Codex · 2026-10-25. W obszarze Wygląd, nad paletami, wybierz
Classic Digital, Industrial Pro, Cyberdeck, Organic Vector albo „Dotychczasowy
widok”. Kliknij „Zapisz widok na następne uruchomienie”. Rodzina zmieni się po
kolejnym uruchomieniu HMI; zapis nie restartuje sterowania ani nie wykonuje ruchu.
Ustawienie jest niezależne od palety i zapisuje się w
`~/.config/linumert/operator-view.json`. Jawna zmienna `LINUMERT_OPERATOR_SKIN`
ma pierwszeństwo; aby użyć zapisu GUI, uruchom bez niej. W nowym widoku przycisk
Ustawienia prowadzi do obszaru Wygląd. Nowa integracja jest w odbiorze;
niepodłączone kontrolki/sceny mają nadal ograniczony zakres opisany w HMI.
