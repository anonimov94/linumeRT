# linumert.alarms

Katalog alarmow (catalog.yaml - jedyne zrodlo: W-xxxx, E-xxxx, K-3xx, P-xxxx) i tlumaczenia.

## Użycie (sesja 007)
- `catalog.yaml` jest jedynym źródłem kodów i tekstów PL/EN; `load_catalog()` waliduje unikalność
  kodów, oba języki, pole `clear` (`auto`/`ack`/`reset`) i zgodność `{pól}` z `params`.
- `AlarmManager` (`manager.py`): `raise_alarm`, `acknowledge`, `clear`, `reset`, `active`,
  `history`, `worst_level`, `subscribe`; bez zależności od UI i LinuxCNC, bezpieczny wątkowo.
- Znaczenia kodów spoza tabeli K z `docs/wymagania/NARZEDZIA_I_KOLIZJE.md` §3 to PROPOZYCJA;
  zmieniasz je w jednym miejscu: `catalog.yaml` (+ test wymaganych kodów w `tests/test_alarms.py`).
- Zasada ekranu: wszystkie nowe teksty interfejsu przez `tr()`; teksty alarmów pochodzą z katalogu.
