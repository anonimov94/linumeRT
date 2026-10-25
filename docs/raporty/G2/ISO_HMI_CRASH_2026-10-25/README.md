# ISO — awaria HMI przy starcie 2026-10-25


## Aktualny stan przeglądu — 2026-10-25

Model-Author: Claude. **Przyczyna ustalona w VM: brak pakietu `xfce4-notifyd` w obrazie**
(SIGSEGV w dbus_connection_dispatch przy powiadomieniach). Poprawka: #157 (scalony,
`xfce4-notifyd` w `linumert.list.chroot`). Próby software GL poniżej nie były przyczyną.
Obraz z poprawką jeszcze nie odebrany na laptopie właściciela.
NIEZWERYFIKOWANE NA SPRZĘCIE.

Model-Author: Codex. Poniższe próby GL są historią diagnostyki, nie zaleceniem
ich powtarzania. Claude później odtworzył awarię w VirtualBox: stos prowadził
przez dbus_connection_dispatch/pthread_mutex_lock, przy braku demona powiadomień.
Po instalacji xfce4-notifyd ekran w VM uruchomił się; pakiet dodano do obrazu.
Źródło: docs/DZIENNIK.md, „ISO — SIGSEGV ekranu przy starcie na laptopie”.
To dowód dla środowiska VM, nie dowód identycznej przyczyny starego raportu laptopa
bez SHA. Następny odbiór dotyczy nowo zbudowanego ISO z tym pakietem: SHA obrazu,
start QtVCP i raport w razie ponownej awarii. Nie blokujemy tego odbioru oczekiwaniem
na ponowienie znanej nieskutecznej próby software GL. Odbiór ISO pozostaje otwarty.

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

## Potwierdzona usterka trybu --safe (nie przyczyna pierwotnej awarii)

Próba z rzeczywistym PyQt5.QtOpenGL.QGLWidget pod Xvfb, bez LinuxCNC i bez ruchu:
LIBGL_ALWAYS_SOFTWARE=1 + QT_XCB_GL_INTEGRATION=none → isValid() False;
LIBGL_ALWAYS_SOFTWARE=1 + QT_XCB_GL_INTEGRATION=xcb_glx → isValid() True.
Bazowy widget QtDragon wymaga GL, więc wyłączenie integracji Qt w --safe nie jest
poprawnym sposobem wymuszenia renderowania programowego.

Launcher --safe zachowuje LINUMERT_NO_GL=1 dla pyqtgraph i używa programowego Mesa
z QT_OPENGL=software oraz QT_XCB_GL_INTEGRATION=xcb_glx. Regresja uruchamia launcher
z atrapą interpreter/CNC, przechwytuje faktyczne środowisko, następnie sprawdza
prawidłowy kontekst rzeczywistego QGLWidget. Nie dotyka procesów CNC.
12 testów ISO/regresji PASS, ruff PASS. Pierwszy ręczny transfer skryptu z NTFS do
snapshotu miał CRLF; po normalizacji LF odpowiadającej zapisowi Git test składni PASS.

Na już nagranym ISO poprzednia prośba o --safe jest zastąpiona tą próbą (bez --safe):

```sh
PYTHONFAULTHANDLER=1 LINUMERT_NO_GL=1 LIBGL_ALWAYS_SOFTWARE=1 \
QT_OPENGL=software QT_XCB_GL_INTEGRATION=xcb_glx linumert
```

To nie uruchamia drugiego serwera Plant. Wynik laptopa nadal oczekiwany; poprawny
kontekst Qt pod Xvfb nie dowodzi usunięcia pierwotnego SIGSEGV przy normalnym starcie.

## Wynik próby właściciela: nadal się zamyka

Właściciel odpowiedział na poprawioną próbę bez --safe (software Mesa, xcb_glx,
faulthandler): **„Nadal się zamyka”**. Korekta integracji GL nie rozwiązała
zgłoszonego problemu. To nadal wymaga nowego raportu z faulthandler; nie wiadomo,
czy zakończenie ma ten sam stos co pierwotny SIGSEGV.

W lokalnym Downloads są wyłącznie pierwotne linuxcnc.report/info z 14:18 UTC;
nie traktujemy ich jako nowego wyniku. Wymagany plik z ISO właściciela:
~/linuxcnc_debug.txt lub nowy linuxcnc.report po tej próbie. Bez ponownego pytania
czy software GL uruchamia ekran — ten wynik już otrzymano.

#156 jest scalony jako 6dc700f, a #153/#155 są również w main. Dostępny obraz
iso-20261025-6dc700f nie jest automatycznie obrazem testowanym wcześniej przez
właściciela; brak SHA w przesłanym raporcie. Żadne scalenie ani zielone CI nie
stanowi potwierdzenia startu na jego laptopie.
