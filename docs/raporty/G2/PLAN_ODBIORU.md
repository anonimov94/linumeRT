# Plan odbioru linumeRT — od G2 do wydania alfa

Model-Author: Codex

Najpierw domykamy odbiór operatorski G2 na LinuxCNC z Plant. Po zaliczeniu
próby operatorskiej i przeglądzie ekranów przechodzimy do G3.
Aktualne statusy i powiązania zadań są w [roadmapie](../../roadmap/plan.json).
Dowody odbioru zapisujemy w [raporcie G2](../G2.md).

## G2 — WebHMI i obsługa operatorska

| Kolejność | Zadanie | Kryterium odbioru |
|---|---|---|
| 1 | MPG, blokady trybu i zatrzymanie | Obrót koła w MDI i AUTO nie wywołuje ruchu. STOP zatrzymuje aktywny ruch. Po powrocie do JOG wcześniejsze impulsy nie uruchamiają osi. Powtórna próba przechodzi dla 9 kombinacji XYZ i kroków 1/10/100 µm. |
| 2 | Ręczna zmiana narzędzia | WebHMI pokazuje właściwy numer narzędzia. Potwierdzenie pozwala kontynuować program. Anulowanie kończy próbę w udokumentowanym stanie. |
| 3 | Awaria napędu w AUTO | WebHMI pokazuje awarię i blokuje wznowienie przy aktywnej przyczynie. Po usunięciu przyczyny operator może potwierdzić alarm i świadomie odzyskać pracę odpowiednią procedurą. |
| 4 | Pełny przejazd operatorski | Włączenie, bazowanie, JOG, sonda, zmiana narzędzia i zakończenie AUTO w jednym przebiegu. Sprawdzenie obsługi klawiaturą w 1280×768 i 1920×1080, z raportem i zrzutami. |
| 5 | Zamknięcie bramki | Zielona regresja, rozliczone pozostałe kryteria M2 i niezależny przegląd ekranów. Ręczny odbiór stanowiska VM/Plant z G1 ma odrębny [protokół](../G1.md). |

Prace nad MPG [PR #237](https://github.com/anonimov94/linumeRT/pull/237).

## G3–G6 — odbiór kolejnych prototypów

| Bramka | Wynik do uzyskania |
|---|---|
| G3 — programowanie dialogowe | Utworzyć program z pięciu operacji dialogowych, wygenerować `.ngc`, wykonać go na Plant bez alarmów i zapisać czas oraz uchyby nadążania. |
| G4 — symulacja i kolizje | Na trzech programach porównać czas symulacji z Plant. Potwierdzić różnicę do 10% i wykrywanie przypadków K-301/K-302. |
| G5 — konfiguracje maszyn | Uruchomić pięć konfiguracji na Plant, w tym maszynę 5-osiową i konfigurację z ATC. |
| G6 — alfa | Zainstalować linumeRT na czystej VM z Debianem 12 i LinuxCNC 2.9, przejść pełną regresję i przegląd przed wydaniem alfa. |
