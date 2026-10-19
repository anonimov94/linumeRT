# Zero detalu: przygotówka i podgląd offline

Model-Author: Codex · 2026-10-19.

Z katalogu repozytorium uruchom `bash tools/dev/preview-zero.sh`.
Otwiera się osobny edytor: bez LinuxCNC i QtVCP. Ustawianie zer jest zablokowane,
a zapisy trafiają do katalogu tymczasowego usuwanego po zamknięciu. Kontener podglądu
nie ma sieci, a repozytorium jest zamontowane tylko do odczytu.

- Wybierz prostopadłościan, walec, rurę albo **Odlew**.
- Rura ma osobną średnicę zewnętrzną i średnicę otworu.
- Profil odlewu to jedna strona konturu: **Z** wzdłuż osi, **R** jako odległość od osi
  (promień, nie średnica). Punkty Z muszą rosnąć. Bryła powstaje przez obrót o 360° wokół Z.
- Dodawaj/edytuj punkty w tabeli; półprofil i bryła 3D aktualizują się od razu.
- Przeciągaj myszą, aby obracać widok; kółko zmienia powiększenie. Przyciski kamery
  pokazują całą maszynę lub sam detal. Formularz przewija się na niskich ekranach.

W pełnym HMI obszar **Zero detalu** używa tego samego widoku. Zapis przygotówki trafia
do `linumert_workpiece.json` przy konfiguracji maszyny. „Ustaw G54…G59” wymaga bazowania,
postoju programu i potwierdzenia; wysyła `G10 L2` przez ACTION, bez polecenia ruchu osi.
Geometria pokazuje nominalną przygotówkę; aktualnie skrawany materiał ogląda się w Symulacji.

Zrzut rzeczywistej aplikacji offline: [podgląd](raporty/zero_detalu/offline.png).

„Wczytaj bazę z maszyny” w pełnym HMI pobiera wybrany G54–G59 z bieżącej konfiguracji
(aktywny układ na żywo, pozostałe zapisane w PARAMETER_FILE). Pola można następnie edytować
z dokładnością wpisu 0,0001 mm. Dopiero potwierdzony przycisk „Ustaw” zmienia układ LinuxCNC.
