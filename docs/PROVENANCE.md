# Rejestr pochodzenia zasobów

Każdy zasób (ikona, font, grafika, biblioteka, kod z innego projektu) ma tu wpis: autor, data, źródło,
licencja, zakres użycia. Zasady: `docs/prawne/WYTYCZNE_IP.md` §4 pkt 4. Sesja 002 rozbuduje ten rejestr;
sesja 001 zakłada go i wpisuje zasoby istniejące w repozytorium.

| Zasób | Autor | Data | Źródło | Licencja | Zakres użycia |
|---|---|---|---|---|---|
| `docs/design/marka/*` (znak, logotyp, tablica marki, baner) | projekt własny linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later (jak kod) | marka linumeRT |
| `docs/design/ikony/*.svg` (31 ikon) | projekt własny linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | ekran, panel Plant |
| `docs/design/makiety/*.png` (01–09) | projekt własny linumeRT (agent AI na zlecenie właściciela) | 2026-10-17 | rysowane od zera | GPL-2.0-or-later | makiety wzorcowe, bez użycia w produkcie |
| `docs/design/tokens.yaml` | projekt własny linumeRT | 2026-10-17 | własny | GPL-2.0-or-later | źródło stylu ekranu i panelu |
| `LICENSE` | Free Software Foundation | 1991 | pakiet `base-files` Debiana (`/usr/share/common-licenses/GPL-2`) | GPL-2.0 (tekst licencji) | licencja projektu |

Fonty wskazane w `tokens.yaml` (IBM Plex Sans, JetBrains Mono) nie są jeszcze dołączone do repozytorium;
wpis licencji (SIL OFL 1.1) pojawi się przy dodaniu plików fontów.
