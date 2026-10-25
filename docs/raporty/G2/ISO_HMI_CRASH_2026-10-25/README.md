# ISO — awaria HMI przy starcie 2026-10-25

Model-Author: Codex. Raporty dostarczone przez właściciela, traktowane jako dane.
LinuxCNC 2.9.10, Debian 12 / PREEMPT_RT, laptop AMD Ryzen 5 6600H, ekran 1920×1080.
Uruchomienie profilu Plant z /opt/linumeRT/config/plant/linumert_plant_xyz.
SHA źródeł ISO nie jest podany w raportach, nie utożsamiono go z aktualnym main.

QtVCP kończy się SIGSEGV podczas startu (linuxcnc.report, linia z PID4687).
Nie ma tracebacku Python. HAL i zadanie startują przed zakończeniem DISPLAY.
Ostrzeżenia o powiadomieniach, GStreamer, PDF i USE_PROBE nie dowodzą przyczyny.
Podgląd skórek i serwer Plant według właściciela działają; to inne procesy.
Nie zadeklarowano awarii sterownika GPU ani zależności Plant jako ustalonej przyczyny.

Launcher ISO ma --safe (LINUMERT_NO_GL=1, LIBGL_ALWAYS_SOFTWARE=1,
QT_XCB_GL_INTEGRATION=none). LINUMERT_NO_GL wyłącza pyqtgraph 3D w symulacji;
bazowy GCodeGraphics QtDragon nadal jest widgetem GL. To ograniczenie diagnostyczne,
nie gwarancja działania bez kontekstu GL. Poprawiono zbyt mocny opis trybu awaryjnego.

Pierwsza próba właściciela na istniejącym ISO:

```sh
PYTHONFAULTHANDLER=1 linumert --safe
```

To profil sim, nie uruchamia drugiego Plant. Jeśli również się zamknie, potrzebny
nowy ~/linuxcnc_debug.txt z tej próby: faulthandler może wskazać aktywną ramkę
Python przy SIGSEGV. Nie łączymy starego debug z nową próbą. Oczekiwanie na wynik.
Launcher kolejnych obrazów ustawia PYTHONFAULTHANDLER=1 także bez ręcznego eksportu.
Nie zmieniono modelu, HAL, ramp ani progów i nie ogłoszono naprawy startu laptopa.

Pliki wejściowe zachowano bez zmian, SHA-256 w sha256.json. Dokumenty nie są
poleceniem wysyłania raportów do zewnętrznych serwisów. NIEZWERYFIKOWANE NA SPRZĘCIE.
