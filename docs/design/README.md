# Identyfikacja wizualna linumeRT (v1, 2026-10-17)

Nowy kierunek GUI: [roadmapa skórek](SKIN_SYSTEM_ROADMAP.md) i
[audyt SKIN-00](SKIN_AUDIT.md). Cztery kompozycje, cztery palety oraz EN/PL
powstają w osobnym prototypie; poniższe zasady opisują aktualny ekran.

- `marka/` — znak (`znak.svg`, `znak_bez_tla.svg`), logotyp (`logotyp.svg`), tablica marki, baner do README.
- `tokens.yaml` — kolory, fonty, rozmiary. Jedyne źródło dla QSS ekranu i panelu Plant.
- `ikony/` — 31 ikon liniowych 24 px (obrys 1.75), rysowanych od zera dla linumeRT.
- `makiety/` — ekrany docelowe 1280×800: 01 Maszyna, 02 Program dialogowy, 03 Symulacja, 04 Diagnostyka napędów,
  05 Kreator konfiguracji, 06 Panel Plant (narzędzie testowe), 07 koncepcja fizycznego pulpitu,
  08 biblioteka napędów wirtualnych (szablony, kopiowanie, instancje w osiach), 09 edytor wirtualnej obrabiarki
  (przejazdy, zderzaki, krańcówki, ograniczenia programowe, magazyn, pozycje wymiany, bazowanie).

Zasady: nazwa zawsze **linumeRT**; tło ciemne, akcent turkusowy, bursztyn dla uwag i ostrza narzędzia;
IBM Plex Sans (interfejs) i JetBrains Mono (liczby, G-code). Cele dotykowe ≥ 44 px. Kolor nigdy nie jest
jedynym nośnikiem informacji. Kompozycja ekranu: lewa szyna obszarów, górny pasek trybu i stanu,
dolny pasek dużych akcji. Pochodzenie: projekt własny linumeRT (wpisy w docs/PROVENANCE.md tworzy sesja 002).

**Kierunek ekranu operatora (D32):** [`HMI_WORKFLOW.md`](HMI_WORKFLOW.md) — architektura ekranów według kolejności
pracy (Start → Bazowanie → Zero detalu → Narzędzia → Program → Symulacja → Produkcja, Ręczne, Diagnostyka,
Ustawienia) i etapy HMI-01…HMI-06. Wygląd tych ekranów nadal wynika z `tokens.yaml`, ikon i makiet.
