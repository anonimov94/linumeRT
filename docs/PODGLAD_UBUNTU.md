# Podgląd testów w Ubuntu WSL

Model-Author: Codex · 2026-10-17

Ubuntu-24.04 ma zainstalowane TigerVNC, XFCE i terminal XFCE. Skrypt nie instaluje
pakietów ani nie zmienia istniejącego hasła. Wymaga również xauth, mcookie,
xdpyinfo, dbus-run-session, setsid, timeout, python3 oraz pytest do testów.

Z katalogu repozytorium uruchom w Ubuntu:

```bash
bash tools/vm/start-vnc.sh
```

Powstaje lokalny pulpit `:9`, port `5909`, okno TigerVNC Viewer przez WSLg
i terminal `linumeRT-testy` wykonujący testy. Hasło pobierane jest z istniejącego
`~/.vnc/passwd`; przy jego braku utwórz je przez `tigervncpasswd`.
Można też połączyć UltraVNC Viewer z Windows: `127.0.0.1::5909`.

Konsola uruchamiająca musi pozostać otwarta. Ctrl+C zatrzymuje procesy tej sesji.
Zamknięcie samego Viewera nie zatrzymuje pulpitu. Logi pozostają w katalogu
wypisanym przy uruchomieniu. Serwer nasłuchuje wyłącznie lokalnie i wymaga hasła.

Jeżeli pulpit `:9` już działa, użyj innego numeru:

```bash
LRT_VNC_DISPLAY=10 bash tools/vm/start-vnc.sh
```

Wtedy port wynosi `5910`. `LRT_VNC_VIEWER=0` pomija automatyczne otwarcie Viewera.
`LRT_VNC_PASSWORD_FILE` pozwala wskazać inny istniejący plik hasła.
Uruchamianym później aplikacjom testowym przekaż wartości `DISPLAY` i `XAUTHORITY`
wypisane przez skrypt oraz `GDK_BACKEND=x11`, `QT_QPA_PLATFORM=xcb`;
usuń z ich środowiska `WAYLAND_DISPLAY`.

W WSLg `/tmp/.X11-unix` jest montowany tylko do odczytu. Dlatego skrypt uruchamia
Xtigervnc bez standardowego wrappera, używa `-nolisten unix` (połączenie X11 przez
gniazdo abstrakcyjne) oraz `-noreset`. Własny plik Xauthority i wymuszenie X11
zapobiegają otwieraniu terminala poza VNC przez Wayland.

To pulpit do testów oprogramowania, nie test deterministycznego czasu rzeczywistego
ani kwalifikacja sprzętu CNC. Sesja 003 (budowa LinuxCNC) pozostaje osobnym zadaniem.
