# Słownik projektu linumeRT

Własne, opisowe nazwy funkcji (WYTYCZNE_IP.md §6). Nazwy producentów sterowań: `docs/prawne/ZAKAZANE_NAZWY.txt`.

## Terminy projektu
| Termin | Znaczenie |
|---|---|
| MDI | ręczne wpisywanie i wykonywanie pojedynczych bloków G-code (nazwa techniczna LinuxCNC; przed publikacją sprawdzić rejestry znaków — WYTYCZNE_IP.md §2) |
| Układ detalu | układ współrzędnych związany z przedmiotem (G54…G59.3) |
| Układ maszyny | układ współrzędnych związany z maszyną (po bazowaniu) |
| Reset | skasowanie alarmu lub przerwanie programu i powrót do stanu gotowości |
| Parametry użytkownika | zmienne numeryczne i nazwane dostępne w G-code (`#<nazwa>`, `#nnn`) |
| Bazowanie | procedura wyznaczenia położenia odniesienia osi po rozruchu |
| Plant | wirtualna maszyna do testów prototypów |
| Program dialogowy | program tworzony w formularzach cykli (format `.lnx`) |

## Słowa zakazane i zamienniki
Słowa z tej tabeli nie występują w kodzie, UI, konfiguracji ani nazwach plików (`tests/test_ip_guard.py`).
Wyjątek: `docs/` (rzeczowe porównania). Format wierszy w bloku: `słowo -> zamiennik`.

```zakazane
MDA -> MDI
R-parametr -> parametr użytkownika
R-parametry -> parametry użytkownika
Q-parametr -> parametr użytkownika
Q-parametry -> parametry użytkownika
ShopMill -> program dialogowy
ShopTurn -> program dialogowy
ManualGuide -> program dialogowy
Conversational -> program dialogowy
```
