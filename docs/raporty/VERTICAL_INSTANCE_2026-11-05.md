# Prywatna instancja zweryfikowanego zadania

Model-Author: Codex · 2026-11-05. Porcja VERTICAL-RUN, sesje028/029/049/053/061.

`linumert-job-instance KONFIGURACJA --out NOWY_KATALOG --port 8765` tworzy prywatne
`evidence/`, `config/` i `home/`, następnie uruchamia własne procesy Plant i LinuxCNC.
Dowody pozostają niezmienne. LinuxCNC korzysta z odrębnych parametrów, tabeli i HOME.
DISPLAY uruchamia WebHMI z istniejącymi pinami HAL i łańcuchem watchdog/HMI, bez bypassu.
Instancja test-mode i aktywny wcześniejszy LinuxCNC są odrzucane; brak globalnego cleanup.
Po przerwaniu kończymy wyłącznie własne grupy procesów. Logi pozostają w katalogu instancji.

WebHMI pokazuje zadanie i cel. Start/wznowienie są zablokowane w bramie oraz kliencie,
ponieważ kontrola żywego początku, narzędzi i konfiguracji nie jest jeszcze wdrożona.
Stan `instance_loaded` nie jest wynikiem wykonania ani zgodą na ruch. Nie wykonujemy
Reset/ON/bazowania. Istniejące jawne sterowanie operatora pozostaje dostępne zgodnie
z jego blokadami. Odbiór rozruchu i GUI, końcowe CI oraz scalenie tej porcji wymagane.

Pierwsze35 testów instancji/bramy/architektury PASS;41 JS PASS. Fixture raportu w testach
jednostkowych jest skonstruowana; nie udaje wyniku rzeczywistego interpretera.
Potrzebny dalszy etap: kontrola żywego stanu przed Start, wykonanie i trwała telemetria,
przerwania oraz raport poziomu4. NIEZWERYFIKOWANE NA SPRZĘCIE.
