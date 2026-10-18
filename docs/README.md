# Dokumentacja linumeRT

Spis wszystkich dokumentów projektu z jednym zdaniem o każdym. Dokumenty są po polsku. Pierwszeństwo przy
sprzecznościach: `CLAUDE.md` → `DECYZJE.md` → `wymagania/` → specyfikacje → prompty sesji.

## Zacznij tutaj

| Dokument | Po co |
|---|---|
| [`../README.md`](../README.md) | czym jest linumeRT, co już działa, szybki start |
| [`NASTEPNA_SESJA.md`](NASTEPNA_SESJA.md) | **stan bieżący**: tura, PR i plan scalania, następna praca, środowisko, otwarte sprawy |
| [`PROMPT_NOWEJ_SESJI.md`](PROMPT_NOWEJ_SESJI.md) | stały prompt startowy agenta: kolejność lektury, praca, zamknięcie sesji |
| [`../CLAUDE.md`](../CLAUDE.md) | kontrakt dla agentów: stos, struktura repo, RT, bezpieczeństwo, IP, Definition of Done |

## Architektura i specyfikacje

| Dokument | Zakres |
|---|---|
| [`PLANT.md`](PLANT.md) | wirtualna obrabiarka Plant: architektura, protokół LRT-NET v1, model osi i napędów, wrzeciono VFD (§5a), `machine.yaml`, `plant.yaml`, odporność |
| [`HAL_KONTRAKT.md`](HAL_KONTRAKT.md) | kontrakt sygnałów HAL `linumert.*` (D05): osie, wrzeciono, I/O; piny komponentów `lrt_net` i `lrt_cia402` |
| [`RDZEN.md`](RDZEN.md) | rdzeń Pythona: model stanu maszyny, czytnik `linuxcnc.stat`, atrapa |
| [`GCODE_LEKSER.md`](GCODE_LEKSER.md) | lekser i kontrola G-code LinuxCNC (kody P-51xx) |
| [`SLOWNIK.md`](SLOWNIK.md) | nazewnictwo projektu i słowa zakazane |

## Wymagania

| Dokument | Zakres |
|---|---|
| [`wymagania/WIRTUALNA_OBRABIARKA.md`](wymagania/WIRTUALNA_OBRABIARKA.md) | REQ-VD (napędy wirtualne), REQ-VM (obrabiarka), REQ-QA (jakość) — obowiązujące |
| [`wymagania/NARZEDZIA_I_KOLIZJE.md`](wymagania/NARZEDZIA_I_KOLIZJE.md) | typy narzędzi, przygotówka, reguły kolizji |
| [`wymagania/KWALIFIKACJA_RT.md`](wymagania/KWALIFIKACJA_RT.md) | kwalifikacja czasu rzeczywistego i kryteria wydania |
| [`wymagania/MACIERZ.md`](wymagania/MACIERZ.md) | macierz pokrycia: wymaganie → sesja → testy → stan |

## Uruchamianie i testy

| Dokument | Zakres |
|---|---|
| [`PLANT_START.md`](PLANT_START.md) | LinuxCNC (RIP) + Plant: budowa, komponenty HAL, testy z LinuxCNC, warianty (w tym `_vfd`) |
| [`SIM_WSL.md`](SIM_WSL.md) | symulator `config/sim/linumert_xyz` z ekranem (podman na Linuksie, WSL) |
| [`PODGLAD_UBUNTU.md`](PODGLAD_UBUNTU.md) | podgląd testów przez VNC w Ubuntu WSL (Windows) |
| [`../tools/README.md`](../tools/README.md) | narzędzia: kontenery deweloperskie, CI, blokady zasobów, paczka testowa |
| [`../hal/README.md`](../hal/README.md) | komponenty HAL linumeRT |
| [`../config/plant/README.md`](../config/plant/README.md) | konfiguracje LinuxCNC dla Plant i `plant.yaml` |

## Proces i historia

| Dokument | Zakres |
|---|---|
| [`WSPOLPRACA_MODELI.md`](WSPOLPRACA_MODELI.md) | jedyne źródło zasad współpracy Claude i Codex: tury, blokady, małe kroki, scalanie |
| [`DECYZJE.md`](DECYZJE.md) | decyzje: architektura (D01–D23), proces (D24–D31), decyzje techniczne sesji |
| [`DZIENNIK.md`](DZIENNIK.md) | dziennik pracy: spis sesji według numeru i wpisy chronologicznie |
| [`../prompts/README.md`](../prompts/README.md) | plan 84 sesji ze stanem; [`DONE.md`](../prompts/DONE.md) — wykonane |
| [`roadmap/index.html`](roadmap/index.html) | interaktywna mapa planu (kamienie M0–M6) |
| [`raporty/`](raporty/) | raporty kamieni (G0: zrzuty ekranu z symulatora i z Plant) |
| [`archiwum/`](archiwum/) | poprzednie wersje dokumentów stanu (bez mocy obowiązującej) |

## Licencje, IP i wygląd

| Dokument | Zakres |
|---|---|
| [`LICENCJE.md`](LICENCJE.md) | licencja projektu i zależności (obecne i planowane) |
| [`PROVENANCE.md`](PROVENANCE.md) | rejestr pochodzenia każdego zasobu i kodu |
| [`prawne/WYTYCZNE_IP.md`](prawne/WYTYCZNE_IP.md) | wytyczne własności intelektualnej (obowiązkowe) |
| [`prawne/PROCES.md`](prawne/PROCES.md) | proces IP w codziennej pracy |
| [`prawne/LISTA_PRZED_WYDANIEM.md`](prawne/LISTA_PRZED_WYDANIEM.md) | lista kontrolna przed wydaniem |
| [`design/README.md`](design/README.md) | identyfikacja wizualna: znak, tokeny, ikony, makiety 01–09 |
