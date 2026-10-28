# 028/029 — WebHMI: JOG z klawiatury

Model-Author: Codex · 2026-10-27. Baza: main `eb2deea`.

Dodano JOG przytrzymaną Spacją lub Enterem wyłącznie na przycisku konkretnej osi z fokusem. Zwolnienie klawisza i utrata fokusu przycisku wysyłają STOP; autorepeat nie uruchamia ponownie przyrostu. Zachowano podtrzymanie, blokady i obsługę wskaźnika. Pola tekstowe nie obsługują tych skrótów JOG.

## Przyczyna i zakres

Podczas kontynuacji najwcześniejszej otwartej sesji 028 i powiązanego 029 odtworzono brak działania Spacji/Entera na przycisku JOG. Obsługiwane były tylko zdarzenia wskaźnika. Nowe zdarzenia klawiatury są przypisane do tych samych przycisków i korzystają z tego samego cyklu start/podtrzymanie/stop.

Nie dodano globalnych skrótów ruchu. Kombinacje z Ctrl/Alt/Meta/Shift oraz autorepeat nie uruchamiają JOG. Zwolnienie innego klawisza lub wskaźnika nie przejmuje gestu klawiatury. Po utracie połączenia nie następuje automatyczne wznowienie.

## Odbiór przeglądarki

Przeglądarka w aplikacji Codex, Windows, lokalna brama `--fake`, port 8876. To rzeczywista przeglądarka i WebSocket z atrapą maszyny, nie LinuxCNC. Widok 1280×768, przewijana strona; nie jest to odbiór pełnej kompozycji M2 na jednym ekranie.

1. Połączenie przez pole tokenu: ONLINE, DRO aktualne, osie X/Y/Z zbazowane, scena WebGL widoczna.
2. Spacja na Jog X plus, przyrost 0,001: DRO X 0,0000 → 0,0010; ACK jog_increment i ACK jog_stop.
3. Przyrost 0,1, Spacja przytrzymana 600 ms: X 0,0010 → 0,1010. Dziennik pokazuje jedno jog_increment, cztery jog_keepalive i jog_stop. Przytrzymanie nie powtarza kroku.
4. Tryb MDI: wszystkie przyciski JOG zablokowane z powodem „Wymagany tryb MANUAL”. Wpisanie `G0 X1` i Spacji w polu MDI bez wysłania formularza nie zmieniło X (0,1010). Pole wyczyszczono.
5. Powrót do MANUAL, JOG ciągły, Enter przytrzymany 350 ms: X 0,1010 → 3,8510; po zwolnieniu ACK jog_stop i JOG: BEZ RUCHU. Droga w trybie ciągłym zależy od rzeczywistego czasu zdarzeń.
6. Późniejszy odczyt X nadal 3,8510; rozłączenie przez przycisk oznacza DRO jako NIEAKTUALNE i blokuje JOG. Po ponownym połączeniu X pozostaje 3,8510 i JOG: BEZ RUCHU, bez automatycznego wznowienia.
7. Dla 1280×768 szerokość dokumentu 1265 px (brak poziomego przepełnienia), komunikat braku WebGL ukryty. Konsola przeglądarki: brak zarejestrowanych błędów.

Dowody: [DRO i podpowiedź klawiatury 1280×768](WEBHMI_KEYBOARD_2026-10-27/01-keyboard-jog.png), [rozłączenie](WEBHMI_KEYBOARD_2026-10-27/02-disconnected.png) i [odczyty DOM](WEBHMI_KEYBOARD_2026-10-27/browser-result.json). Próba rozłączenia odbyła się po zatrzymaniu, nie podczas ruchu; przerwanie aktywnego gestu jest objęte testami Node, a nie tą próbą GUI.

## Testy automatyczne

- Node `tests/webhmi_js/test_jog.mjs`: 18 PASS, w tym 8 nowych przypadków klawiatury.
- Windows/Python 3.12: static, gateway, app i linuxcnc_backend — 97 PASS. Test linuxcnc_backend używa wstrzykniętego modułu; nie jest odbiorem prawdziwego LinuxCNC.
- Ruff PASS; pokrycie REQ 22/22 PASS.
- Pełna próba Debiana 12/Python 3.11 na rewizji kodu `099691a`: 1703 PASS, 138 SKIP, 169 deselected, 1 FAIL — brak wpisu własnego zrzutu w PROVENANCE. Nie był to błąd funkcji. Dodano wpisy obu zrzutów w `2e8f298`; kontrola IP po poprawce: 10 PASS. Pełnej serii po tej zmianie dokumentacji nie powtarzano.
- Na `2e8f298`: `make lint test-c` PASS i REQ 22/22 PASS. Testy wykonano w natywnej kopii Linuksa; początkową próbę z checkoutu Windows przerwano po potwierdzeniu, że nie odtwarza dowiązań Qt wymaganych przez testy.
- Końcowa kontrola CI Pythona, macierzy Plant i LinuxCNC: [PR #196](https://github.com/anonimov94/linumeRT/pull/196). Oczekujący wynik nie jest PASS ani zgodą na scalenie.

## Pozostałe kryteria

Sesje 028/029 i WEBHMI-POC pozostają częściowe. Nadal wymagane są pełny zakres kompozycji, strony i procedury operatora, MPG, odbiór LinuxCNC/Plant oraz niezależny watchdog HAL i odbiór stanowiska. Nie wprowadzano zmian HAL/RT, makr ATC ani backendu CNC. NIEZWERYFIKOWANE NA SPRZĘCIE.

Autokontrola Codex; bez deklaracji niezależnego przeglądu lub konsultacji.
