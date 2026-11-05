# Werdykt weryfikacji offline

Model-Author: Codex · 2026-11-05. Autokontrola, bez niezależnego przeglądu.

`linumert verify JOB --start X Y Z --out NOWY.json` i endpoint `/api/jobs/NAME/verify`
uruchamiają tę samą rzeczywistą kontrolę co preflight, bez promowania starego raportu
lub wyniku otrzymanego od klienta. Wynik `linumert.job.verification`v1 ma status verified
wyłącznie po dodatnich kontrolach integralności, interpretera, dokładnych limitów,
materiału, zadeklarowanych brył/stref i obciążeń. Nowa/pending/niepełna kontrola nie daje
verified. Brak SDK, geometrii, materiału, błąd lub timeout nadal dają wynik ujemny/niepełny.

Weryfikacja dotyczy obsługiwanego modelu diagnostycznego z opisanymi ograniczeniami.
Zachowuje założony początek nosa/T0/G92=0 i wszystkie ograniczenia raportu materiału.
`verification.execution_authorization` jest zawsze false; `execution` pozostaje
not_started. Przed startem trzeba powiązać pakiet, konfigurację, narzędzia i pozycję
z rzeczywistą instancją LinuxCNC sim/Plant. Samo verify nie odczytuje ani nie steruje CNC.
CLI preflight i dotychczasowy endpoint pozostają diagnostyką ze statusem partial.

WebHMI wywołuje verify istniejącym formularzem, z przyciskiem „Zweryfikuj zadanie offline”.
Kontrole przygotowania i wynik weryfikacji mają osobne nagłówki. Pozytywny wynik ma
czytelny komunikat o wymaganym związaniu z maszyną; nie uruchamia programu.

Pierwszy checkpoint:12 testów bramek werdyktu; regresja rdzenia/CLI/API i statycznego
WebHMI PASS (4 testy wymagające Node pominięte w WSL). Trzy rzeczywiste RIP: kompletne
zadanie verified, brak oprawki incomplete, przekroczone limity rejected. Rzeczywisty
CLI/API verified i utrwalanie identycznego raportu bez zmiany pakietu lub CNC PASS.
GUI, pełna regresja i końcowe CI/scalenie w toku. NIEZWERYFIKOWANE NA SPRZĘCIE.
