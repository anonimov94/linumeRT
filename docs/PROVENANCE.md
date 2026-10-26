# Rejestr pochodzenia zasobów

- `docs/design/SKIN_SYSTEM_ROADMAP.md` — ChatGPT, 2026-10-22, własne wytyczne
  projektu na polecenie właściciela; źródło: PR #85, GPL-2.0-or-later.
  Uzupełnienie rejestru wymagane przez strażnik IP po aktualizacji main.

Każdy zasób (ikona, font, grafika, biblioteka, kod z innego projektu) ma tu wpis: autor, data, źródło,
licencja, zakres użycia, ścieżka. Zasady: `docs/prawne/PROCES.md` i `docs/prawne/WYTYCZNE_IP.md` §4 pkt 4.
Test `tests/test_ip_guard.py` wymaga wpisu dla **każdego** pliku w `docs/design/` oraz dla każdego pliku
graficznego/fontu w repozytorium. Nowy zasób = nowy wiersz w tym samym commicie.

| Zasób | Typ | Autor | Data | Źródło | Licencja | Zakres użycia | Ścieżka |
|---|---|---|---|---|---|---|---|
| kamienie-milowe.png | zrzut (PNG) | projekt linumeRT (Claude na zlecenie właściciela) | 2026-10-24 | zrzut własnej strony stanu projektu generowanej z `docs/roadmap/plan.json` | GPL-2.0-or-later | grafika stanu kamieni milowych na górze README | `docs/raporty/kamienie-milowe.png` |
| baner.png | marka | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | znak, logotyp i baner linumeRT | `docs/design/marka/baner.png` |
| logotyp.svg | marka | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | znak, logotyp i baner linumeRT | `docs/design/marka/logotyp.svg` |
| tablica_marki.png | marka | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | znak, logotyp i baner linumeRT | `docs/design/marka/tablica_marki.png` |
| znak.svg | marka | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | znak, logotyp i baner linumeRT | `docs/design/marka/znak.svg` |
| znak_bez_tla.svg | marka | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | znak, logotyp i baner linumeRT | `docs/design/marka/znak_bez_tla.svg` |
| alarm.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/alarm.svg` |
| atc.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/atc.svg` |
| bazuj.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/bazuj.svg` |
| blok.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/blok.svg` |
| chlodziwo.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/chlodziwo.svg` |
| diagnostyka.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/diagnostyka.svg` |
| dialog.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/dialog.svg` |
| estop.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/estop.svg` |
| jog.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/jog.svg` |
| klucz.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/klucz.svg` |
| konfiguracja.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/konfiguracja.svg` |
| korekcja.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/korekcja.svg` |
| maszyna.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/maszyna.svg` |
| mdi.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/mdi.svg` |
| mpg.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/mpg.svg` |
| narzedzia.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/narzedzia.svg` |
| pauza.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/pauza.svg` |
| plant.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/plant.svg` |
| plik.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/plik.svg` |
| program.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/program.svg` |
| reset.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/reset.svg` |
| siec.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/siec.svg` |
| sonda.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/sonda.svg` |
| start.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/start.svg` |
| stop.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/stop.svg` |
| symulacja.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/symulacja.svg` |
| uzytkownik.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/uzytkownik.svg` |
| wrzeciono.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/wrzeciono.svg` |
| wtyczka.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/wtyczka.svg` |
| wykres.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/wykres.svg` |
| zero.svg | ikona (SVG, 24 px) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/zero.svg` |
| strzalka_dol.svg | ikona (SVG, 24 px) | projekt linumeRT (Claude, sesja 028) | 2026-10-25 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/strzalka_dol.svg` |
| strzalka_gora.svg | ikona (SVG, 24 px) | projekt linumeRT (Claude, sesja 028) | 2026-10-25 | rysowane od zera | GPL-2.0-or-later | ekran operatora i panel Plant | `docs/design/ikony/strzalka_gora.svg` |
| 01_maszyna.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/01_maszyna.png` |
| 02_program_dialogowy.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/02_program_dialogowy.png` |
| 03_symulacja.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/03_symulacja.png` |
| 04_diagnostyka_napedow.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/04_diagnostyka_napedow.png` |
| 05_kreator_konfiguracji.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/05_kreator_konfiguracji.png` |
| 06_panel_plant.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/06_panel_plant.png` |
| 07_pulpit_operatora.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/07_pulpit_operatora.png` |
| 08_napedy_wirtualne.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/08_napedy_wirtualne.png` |
| 09_wirtualna_obrabiarka.png | makieta (PNG 1280×800) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makieta wzorcowa; nie jest zasobem produktu | `docs/design/makiety/09_wirtualna_obrabiarka.png` |
| tokens.yaml | tokeny stylu | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | własny projekt | GPL-2.0-or-later | jedyne źródło stylu (QSS ekranu, panel Plant) | `docs/design/tokens.yaml` |
| README.md | dokumentacja | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | własny tekst | GPL-2.0-or-later | opis identyfikacji wizualnej | `docs/design/README.md` |
| index.html | dokumentacja (HTML) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | własny tekst | GPL-2.0-or-later | plan prac (84 sesje) | `docs/roadmap/index.html` |
| zastrzezeniaprawneopcje.txt | dokument prawny | właściciel projektu | 2026-10-17 | dostarczone przez właściciela | wewnętrzny dokument projektu | wytyczne IP właściciela (tekst oryginalny) | `docs/prawne/zastrzezeniaprawneopcje.txt` |
| LICENSE | licencja | Free Software Foundation | 1991 | /usr/share/common-licenses/GPL-2 (Debian) | GPL-2.0 (tekst licencji) | licencja projektu | `LICENSE` |
| IBM Plex Sans | font | IBM Corp. | gdy dodane | https://github.com/IBM/plex | OFL-1.1 | interfejs ekranu i panelu Plant | (jeszcze niedodany: `fonts/`) |
| JetBrains Mono | font | JetBrains s.r.o. | gdy dodane | https://github.com/JetBrains/JetBrainsMono | OFL-1.1 | liczby, G-code | (jeszcze niedodany: `fonts/`) |

Wiersze fontów dostają ścieżki i pliki `OFL.txt` w `licenses/` przy ich dodaniu (sesja 027).

| Paczka testowa i VNC | kod i dokumentacja | model językowy Codex na zlecenie właściciela | 2026-10-17 | własna implementacja | GPL-2.0-or-later | lokalne testy obu modeli i podgląd Ubuntu | `tools/agent_tests/`, `tools/vm/start-vnc.sh`, `tests/test_agent_runner.py`, `docs/PODGLAD_UBUNTU.md` |
| LinuxCNC 2.9 RIP | zależność deweloperska | LinuxCNC contributors | 2026-10-18 | https://github.com/LinuxCNC/linuxcnc/tree/a33293f46575c809e082e0806e79ab996f982513 | GPL-2.0-or-later, nagłówki upstream | budowa i testy sim; kod poza repo | `tools/ci/build-linuxcnc.sh` |
| QtDragon spike | zrzut testowy upstream | LinuxCNC contributors; zapis Codex | 2026-10-18 | QtDragon z powyższego commita, uruchomiony pod Xvfb | GPL-2.0-or-later, zasoby upstream | dowód testu, nie projekt wyglądu linumeRT | `docs/raporty/spike_qtdragon.png` |
| Biblioteka napędów wirtualnych (7 szablonów + schemat) | dane konfiguracyjne YAML/JSON | model językowy Claude na zlecenie właściciela | 2026-10-18 | własne wartości przykładowe klas napędów; bez danych i nazw producentów | GPL-2.0-or-later | domyślne napędy Plant (REQ-VD-05) | `plant/library/drives/*.yaml`, `plant/library/drives/drive_template.schema.json` |
| Moduły szablonów napędów, CLI i narzędzie sprawdzające | kod (Python, C11) i testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja | GPL-2.0-or-later | walidacja, instancje, klonowanie, zmiany live | `plant/server/linumert_plant/drive_template.py`, `drive_library.py`, `__main__.py`, `plant/core/tools/check_params.c`, `tests/test_drive_library.py` |
| Debian 12 WSL rootfs | środowisko testowe, poza Git | Debian contributors | 2026-10-18 | https://deb.debian.org/debian (bookworm, podpis Release sprawdzany przez debootstrap) | licencje poszczególnych pakietów w ich copyright | izolowane testy LinuxCNC, bez dystrybucji obrazu | `tools/vm/bootstrap-bookworm.sh`, `tools/vm/setup-debian12-wsl.ps1` |
| Serwer i kodek LRT-NET v1 | kod (Python, C11) i testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja protokołu opisanego w docs/PLANT.md | GPL-2.0-or-later | komunikacja Plant ↔ komponent HAL | `plant/server/linumert_plant/lrtnet.py`, `plant/server/` |
| Baza narzędzi (SQLite, tool.tbl) | kod (Python) i testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja; format tool.tbl wg dokumentacji LinuxCNC 2.9 (bez kopiowania kodu) | GPL-2.0-or-later | rdzeń narzędzi | `core/linumert/tools/` |
| Format .lnx i kompilator makr | kod (Python), JSON Schema | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja | GPL-2.0-or-later | programy dialogowe | `core/linumert/programs/` |
| Lekser G-code LinuxCNC | kod (Python) i testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja z opisu języka LinuxCNC 2.9 (bez kodu interpretera) | GPL-2.0-or-later | walidacja w edytorze | `core/linumert/programs/lexer.py` |
| Blokady zasobów (lock.py) | kod (Python) i testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja | GPL-2.0-or-later | koordynacja Claude i Codexa | `tools/lock.py`, `tests/test_lock.py` |

| Walidacja pól ramek LRT-NET (reserved, pad, NaN/Inf wrzeciona) | kod (Python) i testy | pomysł i szkic patcha: model językowy Gemini na zlecenie właściciela; wdrożenie i testy w stylu projektu: model językowy Claude | 2026-10-18 | propozycja przekazana przez właściciela (paczka `linumert_lrtnet_hardening.zip`, patch nieaplikowalny — zmiana wpisana ręcznie) | GPL-2.0-or-later | odrzucanie wadliwych ramek (REQ-QA-03) | `plant/server/linumert_plant/lrtnet.py`, `tests/test_lrtnet.py`, `docs/PLANT.md` §3 |
| Konfiguracja symulatora linumert_xyz | INI, HAL, tool.tbl, programy G-code | model językowy Claude na zlecenie właściciela | 2026-10-18 | na podstawie `configs/sim/qtdragon/qtdragon_xyz/` (qtdragon_metric.ini, qtdragon_postgui.hal) oraz `hallib/core_sim.hal` i `simulated_home.hal` z LinuxCNC 2.9.10 (pakiety linuxcnc.org); zmiany opisane w nagłówkach plików; tool.tbl i programy własne | GPL-2.0 (pliki pochodne LinuxCNC), GPL-2.0-or-later (własne) | symulator z ekranem QtDragon | `config/sim/linumert_xyz/`, `config/sim/nc_files/` |
| Skrypty kontenerów deweloperskich | bash | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja; obrazy debian:bookworm, rootfs linuxcontainers.org, pakiety linuxcnc.org | GPL-2.0-or-later | testy i GUI na laptopie | `tools/dev/` |
| Ekran linumert (kopia bazowa QtDragon) | .ui, .qss, .qrc, handler (Python) | LinuxCNC (QtDragon), kopia: model językowy Claude | 2026-10-18 | LinuxCNC 2.9.10, `share/qtvcp/screens/qtdragon/`, commit 86cdca76fa2a; zmiany w `screens/linumert/UPSTREAM.md` | GPL-2.0 (upstream), GPL-2.0-or-later (`linumert_handler.py`) | ekran operatora | `screens/linumert/` |
| Grafiki ekranu QtDragon (przyciski, ikony) | PNG | LinuxCNC (QtDragon) | 2026-10-18 | LinuxCNC 2.9.10, `share/qtvcp/screens/qtdragon/images/`, bez zmian | GPL-2.0 | ekran operatora do czasu własnego zestawu z docs/design | `screens/linumert/images/a_minus_jog_button.png`, `screens/linumert/images/a_plus_jog_button.png`, `screens/linumert/images/atc_spindle_tool.png`, `screens/linumert/images/b_minus_jog_button.png`, `screens/linumert/images/b_plus_jog_button.png`, `screens/linumert/images/brushed_metal.png`, `screens/linumert/images/checked.png`, `screens/linumert/images/c_minus_jog_button.png`, `screens/linumert/images/c_plus_jog_button.png`, `screens/linumert/images/Left_arrow.png`, `screens/linumert/images/Right_arrow.png`, `screens/linumert/images/silver_dragon.png`, `screens/linumert/images/slide_off.png`, `screens/linumert/images/slide_on.png`, `screens/linumert/images/tool_probe.png`, `screens/linumert/images/u_minus_jog_button.png`, `screens/linumert/images/unchecked.png`, `screens/linumert/images/u_plus_jog_button.png`, `screens/linumert/images/v_minus_jog_button.png`, `screens/linumert/images/v_plus_jog_button.png`, `screens/linumert/images/w_minus_jog_button.png`, `screens/linumert/images/w_plus_jog_button.png`, `screens/linumert/images/x_minus_jog_button.png`, `screens/linumert/images/x_plus_jog_button.png`, `screens/linumert/images/y_minus_jog_button.png`, `screens/linumert/images/y_plus_jog_button.png`, `screens/linumert/images/z_minus_jog_button.png`, `screens/linumert/images/zoom.png`, `screens/linumert/images/z_plus_jog_button.png` |
| Zrzut ekranu bazowego (G0) | PNG | model językowy Claude na zlecenie właściciela | 2026-10-18 | zrzut ekranu linumert (kopia QtDragon) w LinuxCNC 2.9.10 pod Xvfb, `tools/dev/zrzut_ekranu.py` | GPL-2.0 (zawiera grafikę QtDragon) | raport kamienia G0 | `docs/raporty/G0/ekran_bazowy.png` |
| Komponenty HAL lrt_net, lrt_cia402, protokół w C | C (halcompile), testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja z docs/PLANT.md §3; idea gniazda nieblokującego jak hm2_eth (tylko dokumentacja); porównanie z cia402 linuxcnc-ethercat i dbraun1981/hal-cia402 bez kopiowania kodu | GPL-2.0-or-later | master LRT-NET w LinuxCNC | `hal/lrt_net.comp`, `hal/lrt_net_proto.h`, `hal/lrt_cia402.comp`, `hal/tests/` |
| Zrzut ekranu z Plant (G0) | PNG | model językowy Claude na zlecenie właściciela | 2026-10-18 | ekran linumert z konfiguracją config/plant/linumert_plant_xyz i serwerem Plant, LinuxCNC 2.9 RIP pod Xvfb (`tools/dev/plant-gui.sh` + `tools/dev/zrzut_ekranu.py`) | GPL-2.0 (zawiera grafikę QtDragon) | raport kamienia G0/M1 | `docs/raporty/G0/ekran_plant.png` |
| Emulator falownika wrzeciona (hy_vfd, Modbus TCP) | kod (Python), testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja; format ramek i długości odpowiedzi z opisu protokołu i porównania z `hy_comm.c`/`hy_vfd.c` LinuxCNC 2.9 (bez kopiowania kodu); Modbus wg specyfikacji Modbus Application Protocol | GPL-2.0-or-later | wrzeciono VFD w Plant | `plant/server/linumert_plant/vfd.py`, `tests/test_vfd.py` |
| Wariant konfiguracji z falownikiem | INI, HAL, plant.yaml | model językowy Claude na zlecenie właściciela | 2026-10-18 | pochodna `config/plant/linumert_plant_xyz/` (sesja 018); wywołanie `hy_vfd` wg dokumentacji komponentu LinuxCNC | GPL-2.0-or-later | LinuxCNC + hy_vfd + Plant | `config/plant/linumert_plant_xyz/linumert_plant_xyz_vfd.ini`, `spindle_vfd.hal`, `spindle_sim.hal`, `plant_vfd.yaml`, `tests/test_plant_vfd_linuxcnc.py` |
| Projekt HMI według kolejności pracy | dokument (Markdown) | autor PR #31 na koncie właściciela; pisownia nazwy poprawiona przez Claude | 2026-10-18 | własny projekt; baza QtDragon 2.9.10 tylko jako kontekst techniczny, bez kopiowania treści | GPL-2.0-or-later | kierunek ekranu operatora (D32) | `docs/design/HMI_WORKFLOW.md` |
| uPlot 1.6.31 | biblioteka JavaScript (min.) i CSS | Leon Sorokin | 2026-10-18 | npm `uplot@1.6.31` (registry.npmjs.org), pliki `dist/uPlot.iife.min.js`, `dist/uPlot.min.css`, `LICENSE` bez zmian; SHA-256 js 2d27e8ad…4921a2, css df630c6a…35fa04 | MIT | wykresy telemetrii panelu Plant | `plant/server/linumert_plant/panel/static/vendor/uPlot.iife.min.js`, `plant/server/linumert_plant/panel/static/vendor/uPlot.min.css`, `plant/server/linumert_plant/panel/static/vendor/uPlot.LICENSE` |
| Panel web Plant | kod (Python, HTML, CSS, JS), testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja; wygląd wg `docs/design/makiety/06_panel_plant.png`, kolory z `docs/design/tokens.yaml` | GPL-2.0-or-later | narzędzie testowe Plant (sesja 022) | `plant/server/linumert_plant/panel/`, `tests/test_panel.py`, `tests/test_panel_parts.py` |
| Znak i ikony w panelu Plant | SVG (kopie bez zmian) | projekt linumeRT (agent AI na zlecenie właściciela) | 2026-10-18 | kopie `docs/design/marka/znak.svg` i `docs/design/ikony/*.svg` | GPL-2.0-or-later | panel Plant | `plant/server/linumert_plant/panel/static/znak.svg`, `plant/server/linumert_plant/panel/static/ikony/klucz.svg`, `plant/server/linumert_plant/panel/static/ikony/mpg.svg`, `plant/server/linumert_plant/panel/static/ikony/plant.svg`, `plant/server/linumert_plant/panel/static/ikony/siec.svg`, `plant/server/linumert_plant/panel/static/ikony/wykres.svg` |
| Scenariusze Plant, runner, raport, awarie, check_requirements | kod (Python), YAML, G-code, testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja (sesja 024) | GPL-2.0-or-later | testy prototypu na Plant | `plant/scenarios/`, `plant/server/linumert_plant/faults.py`, `scenario.py`, `scenario_linuxcnc.py`, `report.py`, `tools/run_scenario.py`, `tools/check_requirements.py`, `docs/raporty/prototypy/` |
| Edytor maszyny i napędów, widok 3D, zakładka awarii w panelu Plant | kod (Python, JS, CSS), YAML, testy | model językowy Claude na zlecenie właściciela | 2026-10-18 | własna implementacja (sesja 023); rzut 3D bez bibliotek; wygląd wg makiet 08–09 i tokens.yaml | GPL-2.0-or-later | panel Plant | `plant/server/linumert_plant/panel/editor.py`, `panel/static/editor.js`, `plant/scenarios/edit_reload.yaml`, `tests/test_editor_api.py` |
| Skrypty maszyn wirtualnych VM-A i VM-B | kod (PowerShell, bash, Python), preseed, systemd, testy | model językowy Claude na zlecenie właściciela | 2026-10-19 | własna implementacja (sesja 025); polecenia `VBoxManage` wg dokumentacji VirtualBox 7, preseed wg dokumentacji instalatora Debiana 12 (pola `@@VBOX_INSERT_…@@` z szablonów `unattended` VirtualBoxa, bez kopiowania plików), bez kopiowania cudzych skryptów | GPL-2.0-or-later | tworzenie i instalacja VM, usługa Plant, most falownika, pomiar łącza | `tools/vm/vm.conf`, `create-vms.ps1`, `PSScriptAnalyzerSettings.psd1`, `preseed-plant.cfg`, `lib.sh`, `post-install-ctl.sh`, `post-install-plant.sh`, `lrtnet_probe.py`, `docs/VM.md`, `tests/test_vm_scripts.py`, `tests/test_vm_link.py` |
| Nakładka HMI linumeRT na QtDragon (HMI-PoC) | kod (Python, QSS z tokenów), testy, zrzuty | model językowy Claude na zlecenie właściciela | 2026-10-19 | własna implementacja; układ wg `docs/design/makiety/01_maszyna.png` i `HMI_WORKFLOW.md`, kolory i rozmiary z `tokens.yaml`, ikony `docs/design/ikony/`; API QtVCP (Status/Action/Info) LinuxCNC 2.9 użyte bez kopiowania kodu | GPL-2.0-or-later | ekran operatora | `screens/linumert/linumert_shell.py`, `linumert_shell_model.py`, `linumert_shell_selftest.py`, `linumert_handler.py`, `tests/test_hmi_shell_model.py`, `tests/test_hmi_shell_gui.py`, `docs/raporty/hmi_poc/04_bazowanie.png`, `docs/raporty/hmi_poc/11_wznowiony.png`, `docs/raporty/hmi_poc/17_obszar_qtdragon.png`, `docs/raporty/hmi_poc/20_start.png`, `docs/raporty/hmi_poc/21_diagnostyka.png`, `docs/raporty/hmi_poc/22_produkcja.png`, `screens/linumert/linumert_shell_pages.py` (etap 2; zrzuty samotestu, LinuxCNC 2.9 RIP + Plant pod Xvfb) |
| Starter aplikacji linumeRT | skrypt bash (Containerfile w treści), testy | model językowy Claude na zlecenie właściciela | 2026-10-19 | własna implementacja; obraz Debian 12 + pakiety LinuxCNC 2.9 z linuxcnc.org (klucz sprawdzany po odcisku, jak `tools/dev/linuxcnc-gui.sh`), pydantic/FastAPI/Uvicorn z PyPI w obrazie (licencje: `docs/LICENCJE.md`) | GPL-2.0-or-later | uruchomienie jednym poleceniem, skróty w menu | `tools/linumert-start.sh`, `tests/test_launcher.py` |
| Grzyb E-STOP w HMI w łańcuchu HAL (D35) | HAL, kod (Python), testy | model językowy Claude na zlecenie właściciela | 2026-10-19 | własna konfiguracja; komponenty LinuxCNC 2.9 `watchdog`, `logic`, `or2`, `estop_latch` (GPL-2, używane, nie kopiowane) | GPL-2.0-or-later | łańcuch E-STOP symulatora i Plant | `config/hal/linumert_hmi_estop.hal`, `tests/test_hmi_estop_hal.py` |

| Widok Bazowanie HMI | kod Python i testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | własna implementacja według HMI_WORKFLOW.md, istniejące tokeny i API QtVCP; bez kopiowania kodu | GPL-2.0-or-later | stan stawów, bazowanie, nawigacja | `screens/linumert/linumert_homing_page.py`, `tests/test_hmi_workflow_widgets.py` |

| Widok Program HMI | kod Python, testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | własna implementacja wg HMI_WORKFLOW.md, API QtVCP użyte bez kopiowania kodu | GPL-2.0-or-later | wybór, podgląd i jawne wczytanie G-code | `screens/linumert/linumert_program_page.py`, `tests/test_hmi_workflow_widgets.py` |
| Symulacja HMI: materiał 2.5D, kolizje, przeciążenia; widoki Symulacja i Narzędzia | kod (Python), konfiguracja, programy przykładowe, testy, zrzuty | model językowy Claude na zlecenie właściciela | 2026-10-19 | własna implementacja (mapa wysokości, profile narzędzi z `NARZEDZIA_I_KOLIZJE.md`); widok 3D przez pyqtgraph.opengl (MIT, pakiet Debiana, bez kopiowania kodu); API LinuxCNC (`linuxcnc.stat`/`command`) | GPL-2.0-or-later | symulacja i ekran operatora | `simulation/linumert_sim/*.py`, `screens/linumert/linumert_sim_page.py`, `screens/linumert/linumert_tools_page.py`, `config/sim/linumert_xyz/machine.yaml`, `tools_seed.yaml`, `linumert.var.default`, `config/sim/nc_files/linumert_demo.ngc`, `linumert_kolizja.ngc`, `tools/dev/sim-e2e.sh`, `tools/dev/sim_e2e_driver.py`, `tests/test_sim_engine.py`, `docs/raporty/hmi_sym/demo_po_obrobce.png`, `docs/raporty/hmi_sym/demo_w_trakcie.png`, `docs/raporty/hmi_sym/kolizja_k302.png` (zrzuty z `tools/dev/sim-e2e.sh`, LinuxCNC 2.9 pod Xvfb) |

| Monitor postępu HMI | skrypt Python | model językowy Codex na zlecenie właściciela | 2026-10-19 | własna implementacja, biblioteka standardowa | GPL-2.0-or-later | lista kroków w terminalu | `tools/dev/hmi-progress.py` |

| Przygotówka parametryczna i odlew obrotowy | kod Python, testy | model językowy Codex na zlecenie właściciela | 2026-10-19 | własna geometria siatek: BOX, walec, rura, profil Z/R obracany 360° | GPL-2.0-or-later | Zero detalu HMI | `core/linumert/programs/workpiece.py`, `tests/test_workpiece.py` |

| Widok brył Zero detalu | kod Python i testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | własna projekcja 3D i rasteryzacja Qt, bez OpenGL; kolory z tokens.yaml | GPL-2.0-or-later | obrót i zoom maszyny/przygotówki | `screens/linumert/linumert_workpiece_view.py`, `tests/test_workpiece_view.py` |

| Edytor profilu odlewu | kod Python, testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | własny wykres jednej strony konturu Z/R, edytowalna tabela | GPL-2.0-or-later | przygotówka obrotowa w Zero detalu | `screens/linumert/linumert_profile_editor.py`, `tests/test_workpiece_view.py` |

| Własna strona Zero detalu | kod Python, testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | własny formularz przygotówki i położenia, istniejące tokeny | GPL-2.0-or-later | BOX, walec, rura i odlew w maszynie | `screens/linumert/linumert_offsets_page.py`, `tests/test_hmi_workflow_widgets.py` |

| Podgląd offline Zero detalu | kod Python, testy Qt | model językowy Codex na zlecenie właściciela | 2026-10-19 | niezależny proces Qt bez importowania LinuxCNC/QtVCP, pliki tymczasowe | GPL-2.0-or-later | bezpieczna edycja przygotówki | `tools/dev/preview-zero.py`, `screens/linumert/linumert_view_helpers.py` |

| Podgląd offline Zero detalu i launcher | własny zrzut aplikacji Qt i skrypt bash | model językowy Codex na zlecenie właściciela | 2026-10-19 | zrzut `preview-zero.py --snapshot`, kontener podglądu bez sieci, repo tylko do odczytu | GPL-2.0-or-later | bezpieczna edycja przygotówki | `tools/dev/preview-zero.sh`, `docs/raporty/zero_detalu/offline.png` |
| Zrzuty odbioru rodzin skórek w hoście QtVCP (#163) | PNG | model językowy Claude na zlecenie właściciela | 2026-10-25 | prawdziwe HMI w LinuxCNC 2.9 pod Xvfb, rodzina wybrana zmienną `LINUMERT_OPERATOR_SKIN`, okna 1920×1080 i 1280×800, bez retuszu | GPL-2.0-or-later (zawiera grafikę QtDragon) | odbiór SKIN-04…06 / 028 | `docs/raporty/G2/skorki_qtvcp/classic-digital_1280x800.png`, `docs/raporty/G2/skorki_qtvcp/classic-digital_1920x1080.png`, `docs/raporty/G2/skorki_qtvcp/cyberdeck_1280x800.png`, `docs/raporty/G2/skorki_qtvcp/cyberdeck_1920x1080.png`, `docs/raporty/G2/skorki_qtvcp/industrial-pro_1280x800.png`, `docs/raporty/G2/skorki_qtvcp/industrial-pro_1920x1080.png`, `docs/raporty/G2/skorki_qtvcp/organic-vector_1280x800.png`, `docs/raporty/G2/skorki_qtvcp/organic-vector_1920x1080.png` |
| Obszar „Wygląd” HMI (palety, edytor kolorów) | kod (Python/Qt), testy, zrzuty | model językowy Claude na zlecenie właściciela | 2026-10-25 | własna implementacja; wartości palet z `linumert_skin_contract.PALETTES` i `docs/design/tokens.yaml`; zrzuty z LinuxCNC 2.9 pod Xvfb | GPL-2.0-or-later | zmiana kolorystyki HMI | `screens/linumert/linumert_appearance.py`, `screens/linumert/linumert_appearance_page.py`, `tests/test_appearance.py`, `docs/raporty/hmi_appearance/wyglad_neon_punk.png`, `docs/raporty/hmi_appearance/wyglad_classic_turquoise.png` |
| Zakładka „Maszyny” panelu Plant (biblioteka maszyn, edytor YAML) | kod (JS/HTML/CSS), test, zrzut | model językowy Claude na zlecenie właściciela | 2026-10-25 | własna implementacja; zrzut z panelu Plant uruchomionego lokalnie | GPL-2.0-or-later | panel testowy Plant | `plant/server/linumert_plant/panel/static/library.js`, `docs/raporty/plant_biblioteka/zakladka_maszyny_kosz.jpg` |
| Inwentaryzacja HMI-01 | narzędzie Python, test, dokumentacja | model językowy Codex na zlecenie właściciela | 2026-10-18 | własna analiza XML/AST ekranu linumeRT z QtDragon, bez uruchamiania kodu; mapa zawiera nazwy i właściwości z licencjonowanej kopii upstream | narzędzie GPL-2.0-or-later; mapa GPL-2.0 (dane QtDragon) | kontrakt migracji HMI | `tools/hmi_inventory.py`, `tests/test_hmi_inventory.py`, `docs/design/HMI_BASELINE.md`, `docs/design/HMI_WIDGET_MAP.md` |
| Zrzuty odbioru Classic × Neon (N4) | PNG, JSON | model językowy Claude na zlecenie właściciela | 2026-10-25 | zrzuty własnego monitora skórek (`tools/dev/neon_accept.py`) obok LinuxCNC 2.9 sim w AUTO, Xvfb offscreen | GPL-2.0-or-later | raport odbioru N4 | `docs/raporty/neon/01-start.png`, `docs/raporty/neon/02-srodek.png`, `docs/raporty/neon/03-koniec.png`, `docs/raporty/neon/04-preset-ekonomiczny.png`, `docs/raporty/neon/04-preset-zrownowazony.png`, `docs/raporty/neon/04-preset-wysoki.png`, `docs/raporty/neon/neon_accept.json` |

## Obsługa operatora — 2026-10-19

Codex, własny kod GPL-2.0-or-later: `linumert_alarm_panel.py`, `linumert_operator_controls.py`,
`linumert_virtual_session.py`, testy operatora i integracja z powłoką. Projekt według wymagań właściciela D37.
HAL symulatora wykorzystuje standardowy komponent LinuxCNC `timedelay` (GPL-2) do handshake M6;
bez kopiowania kodu komponentu i bez zmian w konfiguracji fizycznej maszyny.
| Koncepcja wycofania i powrotu do obróbki (D38) | dokument projektowy | model językowy Claude na zlecenie właściciela | 2026-10-19 | własny opis; mechanizmy LinuxCNC (external offsets, G2/G3 z Z) opisane bez kopiowania dokumentacji | GPL-2.0-or-later | plan ekranu | `docs/design/WZNOWIENIE.md` |
| Obraz live USB / ISO (live-build) | konfiguracja, skrypty, workflow | Claude; integracja bramki startowej i monitora: Codex | 2026-10-19–2026-10-23 | własna konfiguracja live-build (Debian), pakiety z Debiana i linuxcnc.org instalowane w czasie budowy, bez kopiowania cudzych konfiguracji | GPL-2.0-or-later | dystrybucja; profile sim/Plant przechodzą bramkę uruchomienia; osobny monitor skórek read-only | `tools/iso/`, `.github/workflows/iso.yml`, `tests/test_iso.py` |

## Rozdział safety i symulacji — 2026-10-20

Model-Author: Codex. Własna analiza i implementacja GPL-2.0-or-later na polecenie właściciela:
`docs/bezpieczenstwo/README.md`, diagnostyczny proces `simulation/linumert_sim/live.py`,
komunikaty strony Symulacja, `tests/test_sim_diagnostics.py`, aktualizacja testów i e2e.
Audyt Groka przekazany w czacie był wejściem do krytycznej oceny; bez kopiowania jego schematu
jako zweryfikowanego projektu sprzętowego. Brak nowych zależności i zasobów zewnętrznych.

## Deklaracje profilu i kontrola nadzoru PC — 2026-10-20

Model-Author: Codex. Własny kod GPL-2.0-or-later, biblioteka standardowa:
`core/linumert/machine/deployment.py`, `tests/test_deployment_profile.py`,
`config/hardware/safety-contract.ini.example`; test synchronizacji samotestu GUI
`tests/test_hmi_selftest_sync.py`. Bez nowych zależności i kopiowania schematów sprzętowych.

## Audyt tekstowych HAL offline — 2026-10-20

Model-Author: Codex. Własna implementacja GPL-2.0-or-later z biblioteki standardowej:
`core/linumert/machine/hal_audit.py`, integracja deployment CLI,
`tests/test_hal_audit_offline.py`, `tests/test_deployment_cli.py`,
`docs/bezpieczenstwo/ODBIOR.md`. Bez nowych zależności i kodu zewnętrznego.

## Kontrola procesu interpretera — 2026-10-20

Model-Author: Codex. Własne poprawki `linuxcnc_check.py` i testy `test_interpreter_process.py`,
GPL-2.0-or-later, biblioteka standardowa; bez nowych zależności i kodu zewnętrznego.

## Raport środowiska — 2026-10-20

Model-Author: Codex. Własny kod GPL-2.0-or-later: `core/linumert/diag/doctor.py`,
`linumert_doctor_dialog.py`, integracja Diagnostyki, testy `test_doctor_offline.py`
i `test_doctor_gui.py`. Biblioteka standardowa i istniejący PyQt5; bez nowych zasobów zewnętrznych.

## Kontrola składni w widoku Program — 2026-10-20

Model-Author: Codex. Własna integracja istniejącego leksera, lista i nawigacja Qt,
`linumert_program_page.py`, testy `test_hmi_workflow_widgets.py`; GPL-2.0-or-later.
Bez nowych zależności ani zewnętrznych zasobów.

| Strona Cykle: baza narzędzi, czas obróbki, eksport podprogramów | kod (Python/Qt), testy, zrzut | model językowy Claude na zlecenie właściciela | 2026-10-20 | własna implementacja; zrzut widoku offscreen (Qt, tokeny), czas z rs274 LinuxCNC 2.9 RIP | GPL-2.0-or-later | ekran operatora | `screens/linumert/linumert_cycles_page.py`, `tests/test_hmi_workflow_widgets.py`, `docs/raporty/cykle/cykle_narzedzia_czas.png` |

## Launcher i odbiór HMI — 2026-10-20

Model-Author: Codex. Własne poprawki GPL-2.0-or-later: tools/linumert-start.sh,
tests/test_launcher.py, dokumentacja odbioru i lista tygodnia. Bez nowych zależności runtime.
Cytowanie Exec według specyfikacji freedesktop.org (link w skrypcie); test używa opcjonalnego
systemowego Gio, bez kopiowania jego kodu. Zachowane autorstwo pierwotnego startera Claude.

## Wejście do kieszeni — 2026-10-21

Model-Author: Codex. Własny kod GPL-2.0-or-later: generators/pockets.py,
formularz Cyklów, testy golden/geometrii/materiału/Plant/rs274. Bez kodu zewnętrznego
i nowych zależności. Wersja 1 pozostaje bez zmian w `pockets_v1.py`; nowe kieszenie to v2.

## Geometria i wykańczanie kieszeni — 2026-10-21

Model-Author: Codex. Własny algorytm konturów/offsetów, obrotu, naroży i naddatków;
testy materiału oraz rozszerzenie istniejącej sesji LinuxCNC + Plant Claude.
GPL-2.0-or-later, bez nowych zależności. Opis kierunku skrawania odsyła do przykładu
Sandvik Coromant w planie tygodnia; nie kopiowano kodu ani ilustracji producenta.

## Cykle: .lnx i wybrany krok — 2026-10-21

Model-Author: Codex. Własna integracja istniejącego modelu/kompilatora .lnx Claude
z listą kroków i formularzem Qt; zachowane autorstwo widoku i modelu. GPL-2.0-or-later,
bez nowych zależności. Testy obejmują faktyczne kliknięcia przycisków i pliki na dysku.

## D38: podgląd geometrii — 2026-10-21

Model-Author: Codex. Własne funkcje `programs/resume.py`, kontrola kopii materiału
`linumert_sim/resume.py`, protokół procesu i okno podglądu Qt. GPL-2.0-or-later.
Bez nowych zależności i bez kodu zewnętrznego; użyte dotychczasowe modele materiału
i maszyny Claude. Dokumentacja external offsets wskazana w planie, implementacja HAL otwarta.

## Czas pozostały — 2026-10-21

Model-Author: Codex. Własna integracja estymatora Claude z Produkcją (Qt/wątek tła),
walidacja zakresu modelu, limit Z helisy i porównanie czasów z LinuxCNC + Plant.
GPL-2.0-or-later, bez nowych zależności. Kalibracja nie zmienia parametrów sterowania.

## Raport widoku i oś czasu — 2026-10-21

Model-Author: Codex. Własna integracja obrazu Qt i transportu JSON z istniejącym raportem
Claude; SVG osi czasu i synchronizacja czasów. GPL-2.0-or-later. Użyte istniejące Qt
(LGPL/GPL) i pyqtgraph (MIT), bez kopiowania kodu; dokumentacja Qt wskazana w planie.
Test rzeczywistej kamery 3D pod Xvfb/Mesa i test kliknięcia/HTML.

## Wycofanie w pauzie D38 — 2026-10-21

Model-Author: Codex. Własny kod GPL-2.0-or-later: pause_retract.py, kontroler i panel Qt,
HAL połączeń i testy. Bez nowych bibliotek; użyto standardowych komponentów LinuxCNC.
Interfejs external offsets z dokumentacji LinuxCNC 2.9:
https://linuxcnc.org/docs/2.9/html/motion/external-offsets.html .
Nie skopiowano kodu upstream; bazowy handler QtDragon pozostaje bez zmian.

## Historia diagnostyczna — 2026-10-22

Model-Author: Codex. Własny kod GPL-2.0-or-later: diag/journal.py, linumert_log_view.py
oraz testy; integracja istniejącej Diagnostyki. SQLite i CSV ze standardowej biblioteki
Python, istniejące PyQt5 i tokeny wyglądu. Bez nowych zależności ani zasobów zewnętrznych.

## Filtry narzędzi — 2026-10-22

Model-Author: Codex. Własna zmiana linumert_tools_page.py i test rzeczywistych widgetów
Qt/SQLite, GPL-2.0-or-later. Użyto istniejących typów narzędzi i tokenów wyglądu;
bez nowych bibliotek ani zasobów zewnętrznych.

## Odświeżanie listy narzędzi — 2026-10-22

Model-Author: Codex. Własna poprawka linumert_tools_page.py i regresja Qt/SQLite,
GPL-2.0-or-later. Istniejące QSignalBlocker i model zaznaczenia Qt; bez nowych zależności.

## Eksport narzędzi CSV — 2026-10-22

Model-Author: Codex. Własna integracja istniejącego ToolDB.export_csv z QFileDialog
oraz QSaveFile i testy Qt/SQLite, GPL-2.0-or-later. Bez nowych bibliotek ani zasobów.

## Format liczb całkowitych tabeli narzędzi — 2026-10-22

Model-Author: Codex. Własna poprawka formatowania i regresja Qt, GPL-2.0-or-later.
Bez zależności i zasobów zewnętrznych.

## Zachowanie metadanych narzędzia — 2026-10-22

Model-Author: Codex. Własna poprawka budowania rekordu edytora oraz regresja Qt/SQLite,
GPL-2.0-or-later. Standardowe dataclasses.replace; bez nowych bibliotek i zasobów.

## Wybór ścieżki STL narzędzia — 2026-10-22

Model-Author: Codex. Własny formularz, QFileDialog i testy widgetów Qt/SQLite,
GPL-2.0-or-later. QScrollArea i QFormLayout z istniejącego PyQt5; bez nowych zależności.

## Błędy zapisu tabeli narzędzi — 2026-10-22

Model-Author: Codex. Własna obsługa wyjątków i regresje rzeczywistych przycisków Qt/SQLite,
GPL-2.0-or-later. Standardowe sqlite3 i istniejące API LinuxCNC; bez nowych zależności.

## Podgląd historii narzędzia — 2026-10-22

Model-Author: Codex. Własny linumert_tool_history.py, integracja widoku, ograniczenie
ToolDB.history i testy, GPL-2.0-or-later. Istniejące PyQt5, standardowe json/datetime/SQLite;
bez nowych zależności ani zasobów zewnętrznych.

## Pola oprawki i trwałości narzędzia — 2026-10-22

Model-Author: Codex. Własne pola formularza, walidacja skończonych czasów i testy
core/Qt/SQLite, GPL-2.0-or-later. Standardowe math oraz istniejące PyQt5; bez nowych zależności.

## Walidacja liczb tabeli narzędzi — 2026-10-22

Model-Author: Codex. Własne reguły Tool.validate, wspólne finite_number, bramka eksportu
oraz regresje core/Qt/SQLite, GPL-2.0-or-later. Bez nowych zależności i zasobów.

## Korekcja średnicy w eksporcie tabeli — 2026-10-22

Model-Author: Codex. Własna poprawka Tool.tool_diameter, importu i walidacji oraz
regresje core/symulacji/rs274, GPL-2.0-or-later. Użyto istniejącego Cutter i interpretera
LinuxCNC; bez nowych bibliotek. Reguła D tabeli i G41/G42 zgodna z dokumentacją LinuxCNC 2.9.

## Jednostki tabeli narzędzi w HMI — 2026-10-22

Model-Author: Codex. Własna integracja jednostek INI w tooldata/ToolsPage i regresje
Qt/SQLite/rs274, GPL-2.0-or-later. Istniejące przeliczniki ToolDB, bez nowych zależności.

## Normalizacja jednostek procesu Live — 2026-10-22

Model-Author: Codex. Własne przeliczenie wartości statusu i narzędzi oraz testy
rzeczywistego silnika/mapy materiału, GPL-2.0-or-later. Bez nowych zależności.
Semantykę parametrów WCS sprawdzono w LinuxCNC 2.9, convert_coordinate_system
(USER_TO_PROGRAM_LEN); nie kopiowano kodu:
https://github.com/LinuxCNC/linuxcnc/blob/2.9/src/emc/rs274ngc/interp_convert.cc .

## Wybór WCS przygotówki w Live — 2026-10-22

Model-Author: Codex. Własna reguła wyboru aktualnego/zapisanego WCS i regresje
silnika symulacji, GPL-2.0-or-later. Istniejące status.g5x_index/g5x_offset i parser
parametrów LinuxCNC; bez nowych zależności ani zasobów.

## Wskaźnik niezapisanych zmian narzędzia — 2026-10-22

Model-Author: Codex. Własny stan edycji, reguła QSS z istniejącym tokenem amber i test
klawiatury/przycisków Qt/SQLite, GPL-2.0-or-later. Bez nowych bibliotek i zasobów.

## Potwierdzenie porzucenia formularza narzędzia — 2026-10-22

Model-Author: Codex. Własny dialog, przywrócenie zaznaczenia i testy rzeczywistych
okien/klawiszy Qt/SQLite, GPL-2.0-or-later. Istniejące komponenty PyQt5; bez nowych zasobów.

## Kontrakt prototypu skórek — 2026-10-23

Model-Author: Codex. Własny moduł preferencji, palety prototypowe i testy unittest,
GPL-2.0-or-later. Turkus z istniejącego docs/design/tokens.yaml; kierunek z
SKIN_SYSTEM_ROADMAP.md (Model-Author: ChatGPT, 2026-10-22). Bez nowych bibliotek,
fontów, grafik i kodu producentów. Palety nie stanowią gotowych skórek GUI.

Wspólne napisy prototypu EN/PL: własny katalog i regresje kompletności oraz
rozróżnienia stanów, Model-Author: Codex, 2026-10-23, GPL-2.0-or-later.
Bez zewnętrznych tłumaczeń ani bibliotek.

- `docs/design/SKIN_AUDIT.md` — Codex, 2026-10-23, własny audyt repozytorium
  i plan wdrożenia nowych wytycznych, GPL-2.0-or-later.
- `docs/design/SKIN_SYSTEM_ROADMAP.md` — ChatGPT, 2026-10-22, własna koncepcja
  na polecenie właściciela; źródło: gałąź design/skin-system-roadmap-2026-10-22,
  commit 32e8691. Dokument projektu, GPL-2.0-or-later; bez zewnętrznych grafik.

Manifesty i reguła przełączania prezentacji: własny moduł
screens/linumert/linumert_skin_runtime.py oraz testy test_skin_runtime.py,
Model-Author: Codex, 2026-10-23, GPL-2.0-or-later. Bez kodu i zasobów zewnętrznych.

Podgląd układów Qt: własne screens/linumert/linumert_skin_preview.py,
tools/dev/skin-preview.py i tests/test_skin_preview.py. Model-Author: Codex,
2026-10-23, GPL-2.0-or-later. Bez zewnętrznych grafik/kodu. Istniejące PyQt5,
bez nowej zależności projektu. Font systemowy użyty wyłącznie do testów Windows
nie jest kopiowany ani redystrybuowany. Zrzuty w build/skin-preview/ są lokalnymi
wynikami testów, nie nowymi zasobami produkcyjnymi.

Poprawka lokalizacji kroku JOG przed scaleniem #67: własna walidacja QLocale,
regresje klawiatury C/PL/DE, Model-Author: Codex, 2026-10-23, GPL-2.0-or-later.
Bez nowych zasobów ani bibliotek.

## SKIN-01 — 2026-10-23

Model-Author: Codex. Własny simulation/linumert_sim/render_mesh.py i
 tests/test_render_mesh.py, GPL-2.0-or-later. Scena przecinających się trójkątów
oraz testy obrazu/geometrii opracowane w projekcie; bez zewnętrznych zasobów.
Istniejący stos numpy/PyQt5/pyqtgraph/PyOpenGL, bez nowej zależności produktu.

Własne simulation/linumert_sim/render_scene.py, render_view.py oraz
tools/dev/renderer-preview.py: niezależny podgląd brył XYZ/mm i sterowanie kamerą,
Codex, 2026-10-23, GPL-2.0-or-later. Bez nowych zależności i zasobów zewnętrznych.

Własne tools/dev/renderer-check.py i tests/test_render_gl.py: regresje bufora
OpenGL, cullingu, kamer i interakcji; Codex, 2026-10-23, GPL-2.0-or-later.
Zrzuty są dowodami testowymi w build/skin01 lub artefakcie CI, nie zasobami UI.

`docs/design/SKIN_01_RENDERER.md` — Codex, 2026-10-23; opis i wyniki
odbioru własnego prototypu SKIN-01, GPL-2.0-or-later.

## Podgląd skórek z rendererem — 2026-10-23
Model-Author: Codex. Własny `screens/linumert/linumert_skin_viewports.py`:
sceny offline maszyny bramowej, ścieżki i detalu, GPL-2.0-or-later.
Rozszerzenie własnych skin-preview.py / linumert_skin_preview.py / strings;
bez nowych zależności ani zasobów zewnętrznych. Modele wyłącznie poglądowe.

Wzorce dostarczone przez właściciela: `docs/design/referencje-skin/classic-digital.webp`,
`docs/design/referencje-skin/industrial-pro.webp`, `docs/design/referencje-skin/cyberdeck.webp`,
`docs/design/referencje-skin/organic-vector.webp`. Pobrane 2026-10-23 z
https://megawrzuta.pl/hdimgnec (`linumert-showcase.zip`); według roadmapy obrazy
wygenerowane w rozmowie właściciela. Wyłącznie dokumentacja referencyjna, nie tekstury UI.
Brak osobnej deklaracji licencji obrazów w paczce; nie przypisujemy im GPL kodu.
Własny `screens/linumert/linumert_skin_panel.py`: obudowy rysowane kodem Qt,
Codex, 2026-10-23, GPL-2.0-or-later, bez kopiowania fragmentów bitmap.
`docs/design/referencje-skin/README.md` — własny opis kompozycji oraz zakresu
odbioru, Codex, 2026-10-23, GPL-2.0-or-later. Okrągłe wskaźniki w skin_panel.py
są rysowane kodem Qt; stan nieznany, bez wartości demonstracyjnych udających CNC.

`tools/dev/skin-check.py`: własny odbiór 64 wariantów osadzonych paneli OpenGL
(zrzuty w build/skin-preview), Codex, 2026-10-23, GPL-2.0-or-later.

## Aktualne zrzuty podglądu skórek — 2026-10-23
Własne `docs/raporty/hmi_sym/skin_classic-digital.png`,
`docs/raporty/hmi_sym/skin_industrial-pro.png`, `docs/raporty/hmi_sym/skin_cyberdeck.png`,
`docs/raporty/hmi_sym/skin_organic-vector.png`: świeże zrzuty uruchomionej aplikacji Qt
z main `8483b81`, wykonane przez Codex 2026-10-23 przez tools/dev/skin-check.py,
Radeon/Mesa, 1920×1080. GPL-2.0-or-later; bez montażu bitmap referencyjnych.

Odświeżenie demo 2026-10-23, Codex: usunięto zagnieżdżony komentarz w
`config/sim/nc_files/linumert_demo.ngc`; `tools/dev/sim_e2e_driver.py` wymaga
ukończenia z ostatnim narzędziem T11, aby przerwany program nie przechodził odbioru.
Własne zmiany GPL-2.0-or-later, bez nowych zależności.

Odświeżone `docs/raporty/hmi_sym/demo_w_trakcie.png`,
`docs/raporty/hmi_sym/demo_po_obrobce.png`, `docs/raporty/hmi_sym/kolizja_k302.png`
oraz własne `docs/raporty/hmi_sym/README.md`, `docs/raporty/hmi_sym/wynik-2026-10-23.json`:
Codex, 2026-10-23, GPL-2.0-or-later. Zrzuty uruchomionego HMI na Debianie 12,
LinuxCNC 2.9.10/Xvfb, tools/dev/sim-e2e.sh, kod UI main 8483b81 i poprawione demo
8675777. Okno 1920×1080; bez montażu grafik ani retuszu. Nowe regresje w
tests/test_lexer.py sprawdzają rzeczywiste dostarczone programy demo/kolizji.

## Osobne ekrany skórek — 2026-10-23
Model-Author: Codex. Własny `screens/linumert/linumert_skin_controls.py`:
rysowane kodem Qt prostokątne, ścięte i organiczne obudowy przycisków oraz
poglądowe przełączniki. GPL-2.0-or-later, bez fragmentów bitmap i nowych zależności.
Własny `screens/linumert/linumert_skin_readouts.py`: odczyty osi, F/S, poglądowy
symbol narzędzia i czytelny program przykładowy, Codex, 2026-10-23, GPL-2.0-or-later.
Własny `screens/linumert/linumert_skin_screen.py`: wspólne komponenty paneli
odczytu, powiększania i nieaktywnych konsol; kompozycje należą do osobnych klas
skórek. Codex, 2026-10-23, GPL-2.0-or-later. Bez zależności LinuxCNC/HAL.
Własne osobne moduły ekranów: `screens/linumert/linumert_skin_classic.py`,
`linumert_skin_industrial.py`, `linumert_skin_cyberdeck.py`, `linumert_skin_organic.py`
oraz rejestr `linumert_skin_screens.py`. Codex, 2026-10-23, GPL-2.0-or-later.
Osobne kompozycje i konsole według czterech wzorców właściciela; wspólne tylko
komponenty odczytu i renderer. Bez zależności LinuxCNC/HAL.

Aktualizacja czterech `docs/raporty/hmi_sym/skin_*.png`, Codex, 2026-10-23:
rzeczywiste osobne ekrany Qt z kodu ea2fc39, 1920×1080, bez retuszu. Industrial
w Reactor Green, Cyberdeck w Ion Blue, pozostałe w Classic Turquoise.
Własne kształty rysowane przez QPainter i własne sceny 3D; GPL-2.0-or-later.

Konkurs 04 — własny adapter i host odczytu NML: Codex, 2026-10-23,
GPL-2.0-or-later. `screens/linumert/linumert_skin_status.py`,
`screens/linumert/linumert_skin_monitor.py`, `tools/dev/skin-monitor.py`,
`tests/test_skin_status.py`, `tests/test_skin_monitor_linuxcnc.py`, `raporty/04.md`.
Rozszerzenie własnego AxisReadout o pozycje G53, bez zapożyczeń grafiki/kodu.
Kontrakt API sprawdzony w dokumentacji LinuxCNC 2.9 oraz emcmodule.cc gałęzi 2.9;
korzystanie z API, bez kopiowania implementacji. Test używa konfiguracji sim/axis
z zainstalowanego LinuxCNC (GPL-2.0-or-later), wyłącznie w katalogu tymczasowym.
Aktualizacje własnych `docs/design/SKIN_SYSTEM_ROADMAP.md` i
`docs/design/SKIN_AUDIT.md`; bez nowych zależności i zasobów graficznych.

Konkurs 01, Codex, 2026-10-23: własny moduł
`core/linumert/machine/launch.py` i test `tests/test_launch_gate.py` (GPL-2.0-or-later).
Bramka przed exec LinuxCNC oraz atrapa procesu do prób offline; bez nowych zależności
ani zewnętrznego kodu. Zmiany istniejącego startera i konfiguracji zachowują ich pochodzenie.

## Odbiór stanowiska — konkurs 2 · 2026-10-23
Model-Author: Codex. Własne procedury i szablon:
`docs/raporty/ODBIOR_STANOWISKA.md`, `docs/raporty/SZABLON_ODBIORU.md` oraz raport
`prompts/konkurs-2026-10/raporty/02.md`, GPL-2.0-or-later; oparte na dokumentach
i narzędziach tego repozytorium, bez materiałów zewnętrznych i nowych zależności.
`docs/raporty/odbior-2026-10-23-local.tar.gz`: własne logi, wyniki i zrzuty
z uruchomienia kodu repozytorium w Debianie 12 i odtworzenia OD-01 na hoście,
Codex, 2026-10-23, GPL-2.0-or-later. Dwa zrzuty ekranu bez retuszu;
wejścia YAML z istniejącego repo (zachowane nagłówki autorów), manifest SHA-256.
Wyłącznie dowody testów programowych; bez pomiarów fizycznego stanowiska.
`docs/raporty/odbior-2026-10-23-ci.tar.gz`: pełny log i metadane własnego przebiegu
GitHub Actions 40001235761 dla ffb7037, Codex, 2026-10-23, GPL-2.0-or-later;
manifest SHA-256, bez binariów LinuxCNC i bez nowych zależności.

## Wspólna roadmapa — 2026-10-24

`tools/roadmap.py`, `tests/test_roadmap.py`, `docs/roadmap/plan.json`,
`docs/roadmap/template.html`, `docs/roadmap/README.md` i generowane widoki:
własne opracowanie Codex na polecenie właściciela, GPL-2.0-or-later.
Źródła danych: pierwotny plan z commita `796c6a2`, prompty, dziennik i raporty repozytorium;
bez zasobów zewnętrznych i nowych zależności runtime. Zastępują dawny HTML
z osadzonymi makietami; makiety źródłowe w `docs/design/makiety/` pozostają zachowane.

Edytor G-code: kontrola bieżącej treści, wyszukiwanie/zamiana i testy Qt.
Autor: projekt linumeRT / Codex, 2026-10-24, GPL-2.0-or-later, własny kod
w screens/linumert/linumert_program_editor.py oraz tests/test_hmi_workflow_widgets.py.
Bez nowych bibliotek i zasobów produkcyjnych. Lokalny zrzut build/editor-preview.png
korzysta z fontu systemowego wyłącznie do odbioru, bez jego redystrybucji.

Poprawka logowania Live ISO i raport domknięcia gałęzi: Codex, 2026-10-24,
GPL-2.0-or-later; własny kod `tools/iso/test-live-login.sh`, istniejące skrypty ISO
i `docs/raporty/ZAMKNIECIE_GALEZI_2026-10-24.md`. Test wykorzystuje pakiety
Debiana 12 w jednorazowym kontenerze, bez nowych zależności produkcyjnych poza
user-setup/sudo z Debiana wymaganymi dla konta Live.

`linumert_preview2d.py`: widżet Preview2D wydzielony bez zmiany wyglądu z
`screens/linumert/linumert_cycles_page.py`, autor oryginału Claude (2026-10-19),
wydzielenie Codex (2026-10-24), GPL-2.0-or-later. Podgląd D38 i Cykle
współdzielą rysowanie bez zależności podglądu od kompilatora/pydantic.
Poprawka środowiska `core/linumert/machine/launch.py` i testy regresji:
własny kod Codex, 2026-10-24, GPL-2.0-or-later, bez nowych zależności.

Classic × Neon (Model-Author: Claude, 2026-10-24, GPL-2.0-or-later, kod pisany od zera):
`docs/design/koncepcje/classic_neon_symulacja.html` — koncepcja HTML/Canvas 2D skórki Classic
z paletą neon; znak i ikony wstawione inline z `docs/design/marka/` i `docs/design/ikony/`,
fonty IBM Plex i JetBrains Mono (OFL-1.1, już w tokens.yaml) ładowane z Google Fonts tylko w podglądzie.
`screens/linumert/linumert_neon_view.py` i `linumert_neon_render.py` (renderer QPainter, presety), `core/linumert/programs/toolpath.py`
(model ścieżki), `tools/dev/neon-preview.py` i program `config/sim/nc_files/linumert_neon_demo.ngc`.
Bez nowych zależności i bez cudzych grafik.

## Fonty ekranu — sesja 027 (Model-Author: Claude, 2026-10-24)

Pobrane z repozytoriów autorów, niezmienione; licencje obok plików: `screens/linumert/fonts/OFL-IBMPlexSans.txt` (IBM, plex-sans/LICENSE.txt) i `screens/linumert/fonts/OFL-JetBrainsMono.txt` (JetBrainsMono/OFL.txt). Rejestrowane w aplikacji przez `screens/linumert/linumert_fonts.py`; `tools/gen_qss.py` — własny kod, GPL-2.0-or-later.

| Plik | Rodzaj | Autor | Data | Źródło | Licencja | Użycie | Ścieżka | Suma |
|---|---|---|---|---|---|---|---|---|
| IBMPlexSans-Bold.ttf | font | IBM Corp. | 2026-10-24 | https://github.com/IBM/plex (packages/plex-sans/fonts/complete/ttf) | OFL-1.1 | ekran linumeRT (tokens.yaml: fonty) | `screens/linumert/fonts/IBMPlexSans-Bold.ttf` | sha256 9e6c74a889a700d707613d24548fe4ffa6bc59559a0689d2cf9e133bdcdafb2f |
| IBMPlexSans-Regular.ttf | font | IBM Corp. | 2026-10-24 | https://github.com/IBM/plex (packages/plex-sans/fonts/complete/ttf) | OFL-1.1 | ekran linumeRT (tokens.yaml: fonty) | `screens/linumert/fonts/IBMPlexSans-Regular.ttf` | sha256 975dcda37d80f038dcd143c22e33ca2d97a0cc5a929aace1c749153b0fe1afa5 |
| IBMPlexSans-SemiBold.ttf | font | IBM Corp. | 2026-10-24 | https://github.com/IBM/plex (packages/plex-sans/fonts/complete/ttf) | OFL-1.1 | ekran linumeRT (tokens.yaml: fonty) | `screens/linumert/fonts/IBMPlexSans-SemiBold.ttf` | sha256 a20caf8286023a6a7a85e40b1d2a4ae9fc3e3b1f9eda8f4c542dd4986af67bb1 |
| JetBrainsMono-Bold.ttf | font | The JetBrains Mono Project Authors | 2026-10-24 | https://github.com/JetBrains/JetBrainsMono (fonts/ttf) | OFL-1.1 | ekran linumeRT (tokens.yaml: fonty) | `screens/linumert/fonts/JetBrainsMono-Bold.ttf` | sha256 d22c4f3821d725eb01210d278d95dfcfcaadc34699a06658d47c8a5cc5830ada |
| JetBrainsMono-Regular.ttf | font | The JetBrains Mono Project Authors | 2026-10-24 | https://github.com/JetBrains/JetBrainsMono (fonts/ttf) | OFL-1.1 | ekran linumeRT (tokens.yaml: fonty) | `screens/linumert/fonts/JetBrainsMono-Regular.ttf` | sha256 e6fd0d7e91550b3ed2b735d4312474362c4716edc4fc0577a0f61ed782d5aed1 |


## Grafika postępu README — 2026-10-24 · Codex

| Plik | Rodzaj | Autor | Data | Źródło | Licencja | Użycie | Ścieżka |
|---|---|---|---|---|---|---|---|
| postep-sesji.svg | SVG generowany z danych | projekt linumeRT (Codex) | 2026-10-24 | własny tools/roadmap.py + docs/roadmap/plan.json; paleta docs/design/tokens.yaml | GPL-2.0-or-later | aktualny licznik i podział sesji M0–M6 w README | `docs/raporty/postep-sesji.svg` |

## Odświeżenie zrzutów README — 2026-10-25
Model-Author: Claude, GPL-2.0-or-later. Nowe wersje `docs/raporty/hmi_sym/skin_classic-digital.png`,
`docs/raporty/hmi_sym/skin_industrial-pro.png`, `docs/raporty/hmi_sym/skin_cyberdeck.png`,
`docs/raporty/hmi_sym/skin_organic-vector.png` (`tools/dev/skin-check.py`, Xvfb/Mesa llvmpipe, 1920×1080) oraz
`docs/raporty/hmi_sym/demo_w_trakcie.png`, `docs/raporty/hmi_sym/demo_po_obrobce.png`,
`docs/raporty/hmi_sym/kolizja_k302.png` (`tools/dev/sim-e2e-rip.sh`: LinuxCNC 2.9 RIP + ekran linumeRT pod Xvfb,
przycięte do okna 1700×1080 bez retuszu) i `docs/raporty/hmi_sym/wynik-2026-10-25.json`. Zawierają grafiki QtDragon/LinuxCNC
(GPL-2.0) i własne zasoby projektu. Zastępują wersje z 2026-10-23; użyte biblioteki (pyyaml, pydantic, pyqtgraph) tylko
w środowisku wykonującym zrzuty, bez nowych zależności produktu.

## Specyfikacja ekranu głównego — 2026-10-25
- `docs/design/SPEC_EKRAN_GLOWNY.md` — autor: Codex; własny opis wymagań i kryteriów sesji 028, oparty na promptach oraz dokumentacji linumeRT (HMI_WORKFLOW, HMI_BASELINE, tokens.yaml); GPL-2.0-or-later. Bez nowych grafik, kodu lub materiałów osób trzecich.

## Odbiór M2 / 028 — 2026-10-25
- `docs/raporty/G2/M2_028_2026-10-25_start.png` — zrzut LinuxCNC sim + linumeRT/QtVCP pod Xvfb 1280×768, źródła 6ecda95; wykonanie Codex, bez retuszu. Własne zasoby linumeRT i QtDragon/LinuxCNC (GPL-2.0), całość GPL-2.0-or-later. Wynik i ograniczenia w raporcie M2_028_2026-10-25.

## Kolejne zrzuty M2 / 028 — 2026-10-25
- `docs/raporty/G2/M2_028_2026-10-25_v3_01_start.png`, `docs/raporty/G2/M2_028_2026-10-25_v3_16_obszar_narzedzia.png`, `docs/raporty/G2/M2_028_2026-10-25_v3_19_diagnostyka.png` — wykonanie Codex, LinuxCNC sim + QtVCP pod Xvfb 1280×768, źródła e2dde87, bez retuszu; linumeRT i QtDragon/LinuxCNC, GPL-2.0-or-later. Hashe w raporcie followup JSON.

## Dopasowanie kart M2 — 2026-10-25
- `docs/raporty/G2/M2_RESPONSIVE_start.png`, `docs/raporty/G2/M2_RESPONSIVE_tools.png` — Codex, surowe zrzuty rzeczywistego Qt/offscreen, pełna powłoka linumeRT z atrapą CNC, 1280×768, źródła f76554f; własne zasoby projektu i QtDragon/LinuxCNC (GPL-2.0), całość GPL-2.0-or-later. Nie są dowodem wykonania CNC.

## Integracja prezentacji z QtVCP — 2026-10-25
- `docs/design/HMI_QTVCP_HOST.md` — autor: Codex, własna instrukcja implementacji, uruchomienia i odbioru opcjonalnego hosta HMI, oparta na kodzie oraz kontrakcie linumeRT; GPL-2.0-or-later. Bez materiałów osób trzecich i nowych zależności.

- 2026-10-26 · Codex · własne narożniki nakładki Cyberdeck (`linumert_skin_cyberdeck.py`), rysowane Qt z palety projektu; GPL-2.0-or-later; bez zewnętrznych grafik.

### Odbiór Cyberdeck z LinuxCNC — 2026-10-26

Autor: Codex; źródło: własne zrzuty Qt z wykonania programu `linumert_neon_demo.ngc`
w odizolowanym LinuxCNC 2.9.10 / Debian 12 / Xvfb. Licencja: GPL-2.0-or-later
(własna kompozycja i renderer linumeRT; bez zasobów producentów sterowań).
Zakres: dokumentacja techniczna odbioru, bez kwalifikacji sprzętu.

- `docs/raporty/G2/HMI_CLOSEOUT_2026-10-26/01-start.png`
- `docs/raporty/G2/HMI_CLOSEOUT_2026-10-26/02-srodek.png`
- `docs/raporty/G2/HMI_CLOSEOUT_2026-10-26/03-koniec.png`
