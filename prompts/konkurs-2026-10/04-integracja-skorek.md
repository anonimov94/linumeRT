# Konkurs 4 — integracja skórek z działającym HMI

> Specyfikacja historycznego kroku konkursowego. Status i powiązania z pierwotnymi
> sesjami: [wspólny rejestr](../../docs/roadmap/plan.json).

Model-Author: Codex · 2026-10-23

## Cel

Przesuń cztery osobne ekrany offline w stronę rzeczywistego, użytecznego HMI LinuxCNC/QtVCP, zachowując istniejący ekran produkcyjny i jego interlocki. Źródła: `docs/design/SKIN_SYSTEM_ROADMAP.md`, `docs/design/SKIN_AUDIT.md`, `docs/design/HMI_WORKFLOW.md`, `screens/linumert/`, `tools/dev/skin-preview.py`.

## Oczekiwany rezultat

Zbadaj stabilne API QtVCP/LinuxCNC i zbuduj najmniejszy end-to-end pionowy wycinek: bezpieczny, tylko do odczytu stan rzeczywistego LinuxCNC trafia przez jawny adapter do co najmniej jednej osobnej skórki, z obsługą utraty/niedostępności statusu. Dąż do architektury, która pozwoli pozostałym skórkom korzystać z tego samego kontraktu. Jeżeli nie da się bezpiecznie podłączyć tej sesji, przygotuj adapter z atrapą i testami kontraktu oraz dokładny plan integracji.

Kontrolki ruchu pozostają wyłączone, dopóki nie istnieje zweryfikowany, walidowany kanał poleceń z interlockami. Nie dodawaj fasadowych wartości DRO ani udawanego E-STOP. Nie zastępuj obecnego HMI offline preview. Nie wykonuj komend ruchu ani resetu safety.

## Odbiór

- Adapter read-only ma jawne typy, zachowanie przy braku statusu i testy bez LinuxCNC.
- Co najmniej jedna integracja jest sprawdzona w LinuxCNC sim lub pod Xvfb; raport jasno wskazuje środowisko.
- Inne trzy skórki pozostają uruchamialne, a istniejący ekran linumeRT nie ma regresji.
- Wszystkie komendy CNC w niedokończonej integracji są niedostępne; nie omijaj QtVCP/ACTION/HAL.
- Roadmapa, testy i dokumentacja aktualizują stan wdrożenia bez deklaracji pełnej gotowości.

Oddaj wynik według wspólnej punktacji w `README.md`, używając własnego raportu w swojej gałęzi jako `raporty/04.md`. Integracja nie jest odbiorem na sprzęcie.
