# Sondowanie i układy detalu (G54–G59.3): ograniczenia

Model-Author: Claude · 2026-10-25 · sesja 033. Wyniki z LinuxCNC 2.9 + wirtualnej obrabiarki Plant
(`mill_servo_table`). NIEZWERYFIKOWANE NA SPRZĘCIE.

## Układy detalu
- G54…G59, G59.1, G59.2, G59.3 odpowiadają `G10 L2 P1…P9`. Odczyt: `stat.g5x_index` (1…9),
  `stat.g5x_offset`, obrót `stat.rotation_xy`; zapis w pliku zmiennych (parametry 5221, 5241, … 5381).
- Sprawdzone na sim: wszystkie dziewięć układów ustawia się i wybiera, ruch do zera detalu kończy się
  w położeniu maszyny = przesunięcie (±0,01 mm po ustaniu ruchu), układ z obrotem R90 przelicza X/Y.
- „Ustaw zero” w HMI wysyła `G10 L2` przez ACTION po zbazowaniu i w postoju programu.

## Sondowanie G38.x
- Sonda to wejście `motion.probe-input`; w Plant cel sondy (`probe.target` w `machine.yaml`) to
  przygotówka (prostopadłościan) albo płytka; `probe.tip_length` to długość trzpienia.
- Zalecana procedura: **dwa przejazdy** — szybki (np. F100) do znalezienia, odjazd 2 mm, dokładny
  (F10). `G38.2` kończy się błędem, gdy sonda nie zadziała; `G38.3` nie zgłasza błędu.
- Przed ruchem poziomym podnieś Z ponad przygotówkę: sonda wjechana w materiał nie ma jak się cofnąć
  (w Plant bryła przygotówki zatrzymała zjazd trzpienia w materiale).

## Dokładność (Plant, 2026-10-25)
Powtarzalność dokładnego przejazdu: różnica między dwoma przejazdami < 0,001 mm.
Błąd bezwzględny względem geometrii celu: Z −0,011 mm, X +0,016 mm, Y +0,010 mm.
Na osi Z błąd nie zależy od posuwu (F2…F100), więc nie jest opóźnieniem. Źródłem jest luz 10 µm w modelu napędów
(`mechanics.backlash` w `servo_*.yaml`) i sprężystość: LinuxCNC czyta enkoder silnika, a czubek sondy
dochodzi do materiału z luzem. Na prawdziwej maszynie podobny składnik jest typowy i zwykle stały dla kierunku
dojazdu (NIEZWERYFIKOWANE NA SPRZĘCIE), więc **skalibruj sondę na wzorcu o znanym wymiarze** i odejmij stałą poprawkę. Kryterium z promptu
sesji (błąd ≤ 0,01 mm) jest spełnione dla powtarzalności, a dla błędu bezwzględnego tylko na osi Y.

## Kalibracja sondy na wzorcu
Moduł `linumert.programs.probe_calibration` zapisuje stałą poprawkę `prawdziwe − zmierzone` osobno dla każdej
pary oś/kierunek (`X+`, `X-`, `Y+`, `Y-`, `Z-` …) i dla posuwu dokładnego przejazdu. Procedura: zmierz tą samą
metodą (szybki przejazd, odjazd, dokładny F10 dwa razy) ściany wzorca o znanym położeniu; rozrzut powtórzeń
> 0,005 mm albo poprawka > 0,1 mm odrzuca kalibrację. Odczyt w innym kierunku, osi lub z innym posuwem bez
własnej poprawki jest odrzucany. W teście na Plant poprawki wyznaczone w jednym miejscu ściany dały błąd
≤ 0,01 mm w innym miejscu (przesunięcie 20 mm). Poprawka nie zmienia modelu napędów ani LinuxCNC. Na razie
jest to moduł i test; ekranu kalibracji w HMI jeszcze nie ma. NIEZWERYFIKOWANE NA SPRZĘCIE.
