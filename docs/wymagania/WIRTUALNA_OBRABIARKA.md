# Specyfikacja wymagań: biblioteka napędów wirtualnych i konfigurowalna wirtualna obrabiarka (Plant)

Wersja 1.0 · 2026-10-17 · właściciel: użytkownik projektu linumeRT · status: **obowiązująca**

Dokument zamienia wymagania właściciela projektu na mierzalne wymagania z identyfikatorami. Każde wymaganie
ma przypisaną sesję realizującą i co najmniej jeden scenariusz testowy. Pokrycie sprawdza
`tools/check_requirements.py` w CI (REQ-QA-01). **Brak testu dla wymagania = czerwone CI.** Zmiana lub
usunięcie wymagania tylko przez wpis w `docs/DECYZJE.md`.

Słowa „musi” oznaczają wymaganie obowiązkowe, „powinien” zalecane.

## Cel
Umożliwić testowanie każdego prototypu i kamienia milowego linumeRT na **wirtualnej obrabiarce**, która
zachowuje się jak fizyczna maszyna DIY. Jej budowa (kinematyka, osie, napędy, krańcówki, magazyn,
bazowanie) ma być w pełni konfigurowalna, a napędy mają być **kopiowalnymi, parametryzowanymi szablonami**.
Dzięki temu błędy konfiguracji i oprogramowania wyjdą na Plant, a nie na prawdziwej maszynie.

---

## A. Biblioteka napędów wirtualnych (REQ-VD)

| ID | Wymaganie | Sesja | Test (scenariusz / test jednostkowy) |
|---|---|---|---|
| REQ-VD-01 | Napęd jest definiowany **szablonem** (`plant/library/drives/<id>.yaml`) zawierającym: typ (serwo CSP, serwo krokowe, krokowiec open-loop, oś obrotowa z przekładnią, wrzeciono VFD), parametry silnika (krzywa moment–prędkość, J wirnika, stała momentu, prąd znamionowy i szczytowy, rozdzielczość enkodera, hamulec i jego czasy), regulatory (Kp położenia, Kv, Ti, sprzężenia FF), limity (moment, prędkość, okno błędu nadążania i czas okna), reakcje na błędy (quick stop, wyłączenie, hamulec), podzbiór obiektów CiA 402 (6040h, 6041h, 6060h/6061h, 6064h, 607Ah, 603Fh, 6065h, 6072h, 6098h, 6099h, 609Ah). | 013 | `test_drive_template_schema`, `test_drive_template_physics` |
| REQ-VD-02 | Napęd w maszynie jest **instancją**: `template` + `overrides`. Nadpisania są walidowane tymi samymi zakresami co szablon. | 013 | `test_drive_instance_overrides` |
| REQ-VD-03 | **Kopiowanie**: sklonowanie szablonu lub instancji pod nową nazwą (CLI `plant drive clone`, panel), zapis jako nowy szablon z polami `version` i `based_on`. Kopia jest niezależna od oryginału. | 013, 023 | `test_drive_clone_independent`, scenariusz `drive_clone_tuning` |
| REQ-VD-04 | Parametry oznaczone `live: true` (masa, J, tarcie, limit momentu, luz, napięcie) zmieniają się w trakcie pracy; pozostałe po przeładowaniu modelu. Każda zmiana jest logowana z czasem. | 013, 022 | `test_live_params`, scenariusz `heavy_table_live` |
| REQ-VD-05 | Biblioteka startowa (wartości typowe, bez nazw producentów): krokowiec NEMA 23 ok. 3 N·m, krokowiec NEMA 34 ok. 8,5 N·m, serwo krokowe ok. 2,2 N·m, serwo 400 W, serwo 750 W, stół obrotowy ze ślimakiem 1:90, wrzeciono 2,2 kW z falownikiem. | 013 | `test_library_loads_all` |
| REQ-VD-06 | Ten sam format szablonu opisuje napędy rzeczywiste (sekcja `real:` z mapowaniem na lcec/stepgen), żeby konfiguracja przechodziła z Plant na sprzęt bez przepisywania. | 061 | `test_template_real_mapping` |

## B. Konfigurowalna wirtualna obrabiarka (REQ-VM)

| ID | Wymaganie | Sesja | Test |
|---|---|---|---|
| REQ-VM-01 | **Jedno źródło prawdy**: `machine.yaml` opisuje maszynę dla Plant i dla generatora konfiguracji LinuxCNC. Plant nie ma osobnej, ręcznie utrzymywanej kopii parametrów. | 010 | `test_single_source` |
| REQ-VM-02 | **Kinematyka** jako łańcuch członów (liniowy/obrotowy, wektor osi, przesunięcie, rodzic) z presetami: router gantry XYZ (Y na dwóch napędach), frezarka z ruchomym stołem XYZ, XYZA (stół obrotowy), XYZAC trunnion, XYZBC. Mapowanie na kinematyki LinuxCNC. | 010, 014 | scenariusze `kin_gantry`, `kin_xyza`, `kin_trunnion` |
| REQ-VM-03 | **Liczba osi** 3–6 + wrzeciono; przypisanie oś ↔ napęd(y); gantry: dwa napędy na oś z dopuszczalnym rozjazdem i alarmem przekroczenia. | 010, 014 | `gantry_skew_alarm` |
| REQ-VM-04 | **Przejazdy**: zakres mechaniczny osi; **twarde zderzaki** (pozycja, sztywność, tłumienie). Wjazd w zderzak daje zdarzenie `CRASH_HARDSTOP` i — zależnie od konfiguracji — błąd napędu. | 014 | `hardstop_crash` |
| REQ-VM-05 | **Krańcówki** min/max: pozycja zadziałania, histereza, NC/NO, wspólne wejście (łańcuch szeregowy), drgania styków; czujnik bazowy osobny lub wspólny z krańcówką. | 014 | `limit_switch_trip`, `shared_limit_input` |
| REQ-VM-06 | **Ograniczenia programowe**: soft limits z INI oraz **strefy zakazane** (prostopadłościany w układzie maszyny, np. obszar magazynu). Plant jest **wyrocznią testową**: każde zadane położenie poza soft limits lub w strefie zakazanej to błąd testu w raporcie, niezależnie od reakcji LinuxCNC. | 019 | `softlimit_oracle`, `forbidden_zone_oracle` |
| REQ-VM-07 | **Bazowanie po rozruchu**. Po włączeniu maszyna jest niebazowana, pozycja startowa jest losowa (ziarno) w zakresie przejazdu albo wczytana ze stanu. Metody na oś: (a) krańcówka / czujnik bazowy, (b) czujnik + impuls indeksu, (c) **twardy zderzak** z detekcją przez ograniczony moment lub błąd nadążania (próg, czas, zredukowany moment podczas bazowania), (d) enkoder absolutny (bez bazowania; awaria baterii = utrata pozycji), (e) bazowanie w napędzie CiA 402 (tryb 6, metoda z szablonu). Parametry: kierunek, prędkości szukania i powrotu, offset, kolejność osi, wyrównanie gantry na dwóch czujnikach. | 015, 018 | `home_switch`, `home_switch_index`, `home_hardstop`, `home_absolute`, `home_drive_internal`, `home_gantry_square` |
| REQ-VM-08 | **Magazyn narzędzi**: typ (ręczny, regał liniowy, karuzela, parasolowy), liczba gniazd, **położenie i orientacja bazy magazynu** w układzie maszyny, pozycje gniazd (wyliczane lub lista), wysokości podejścia i odjazdu, osłona magazynu (siłownik z czasem), czujniki (obecność narzędzia, osłona, pozycja karuzeli), zacisk wrzeciona (czas, czujnik), przedmuch. | 020 | `atc_rack_geometry`, `atc_carousel_index`, `atc_cover_timing` |
| REQ-VM-09 | **Pozycje wymiany i pomiaru**: pozycja ręcznej wymiany narzędzia, bezpieczna wysokość Z, pozycja i wysokość czujnika długości narzędzia (wejście sondy). | 020 | `manual_change_position`, `toolsetter_measure` |
| REQ-VM-10 | **Bryły kolizyjne** (prostopadłościany i walce): głowica, wrzeciono z narzędziem, stół, magazyn, czujnik narzędzia, imadło. Kolizja → zdarzenie `CRASH` z parą elementów i pozycją. | 020 | `crash_head_magazine` |
| REQ-VM-11 | **Walidacja spójności** przed startem: krańcówki w zakresie przejazdu, soft limits wewnątrz krańcówek, zderzaki za krańcówkami, magazyn i pozycje wymiany osiągalne i poza strefami zakazanymi, liczba osi zgodna z kinematyką. Błędy po polsku ze ścieżką pola. Konfiguracja niespójna nie startuje. | 010, 023 | `test_machine_validation_*` (≥ 15 przypadków) |
| REQ-VM-12 | **Edytor w panelu Plant**: drzewo maszyny, kopiowanie i edycja napędów, przesuwanie magazynu i pozycji wymiany, uproszczony podgląd brył, zapis wersji i przeładowanie modelu bez restartu VM. | 023 | `test_editor_api`, scenariusz `edit_reload` |

## C. Niezawodność (REQ-QA)

| ID | Wymaganie | Sesja | Test |
|---|---|---|---|
| REQ-QA-01 | Każde REQ ma co najmniej jeden test; `tools/check_requirements.py` porównuje tabele z tego pliku z testami i scenariuszami (znacznik `# REQ-XX-NN` w teście lub `requirements:` w YAML scenariusza). Brak = CI czerwone. | 024 | samo narzędzie w CI |
| REQ-QA-02 | Macierz konfiguracji: CI uruchamia zestaw scenariuszy na ≥ 5 przykładowych obrabiarkach (router krokowy gantry, frezarka serwo, XYZA, trunnion, router z ATC). | 024, 082 | job `plant-matrix` |
| REQ-QA-03 | **Odporność**: błędne lub uszkodzone pliki konfiguracyjne (fuzz), restart Plant podczas pracy, utrata połączenia, brak pliku szablonu — proces nie może się zawiesić ani zakończyć niekontrolowanym wyjątkiem; zawsze czytelny komunikat i bezpieczny stan (napędy wyłączone). | 016, 024 | `test_fuzz_machine_yaml`, `plant_restart_midrun`, `link_loss` |
| REQ-QA-04 | **Deterministyczność**: ten sam scenariusz + to samo ziarno = identyczny przebieg (porównanie sum kontrolnych śladów). | 016, 024 | `test_determinism` |

---

## Macierz realizacji
Aktualizowana przez agentów w sesjach oznaczonych wyżej: kolumna „Status” w `docs/wymagania/MACIERZ.md`
(REQ · sesja · test · status: planowane / zaimplementowane / zielone).
