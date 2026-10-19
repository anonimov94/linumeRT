# Prompt startowy: sesja 025, maszyny wirtualne VM-A i VM-B (równolegle z 022 i 024)

Model-Author: Claude · 2026-10-18. Najpierw [`START-PODZIAL.md`](START-PODZIAL.md) (zasady, worktree, testy),
potem pełny zakres w [`sesja-025.md`](../sesja-025.md).

## Zakres w tej sesji
1. Zakres `sesja-025.md` 1–4: `tools/vm/create-vms.ps1` (VBoxManage), `post-install-ctl.sh`,
   `post-install-plant.sh` (usługa systemd `linumert-plant`), `docs/VM.md` krok po kroku.
2. Otwarte sprawy z `docs/NASTEPNA_SESJA.md` §5 dotyczące VM: tryb `--realtime` Plant między dwiema VM
   (jitter, watchdog) opisany i sprawdzony na dwóch instancjach w WSL albo na localhost z opóźnieniem
   (`tc netem`, jeśli dostępne); `socat` dla `hy_vfd` między VM (pty ↔ TCP) z poleceniami w `docs/VM.md`.
3. Istniejące `tools/vm/bootstrap-bookworm.sh`, `setup-debian12-wsl.ps1`, `start-vnc.sh` (Codex): nie
   zmieniaj ich zachowania bez potrzeby; wspólne kroki wydziel, odnośniki w `tools/vm/README.md`.
4. Testy bez VirtualBoxa: `tests/test_vm_scripts.py` (składnia `bash -n`, shellcheck, jeśli jest w WSL;
   preseed i parametry VM zgodne z `docs/VM.md`; brak sekretów w skryptach). VirtualBoxa nie instaluj:
   uruchomienie VM to punkt „do sprawdzenia ręcznie” dla właściciela.

## Kryteria akceptacji
Z `sesja-025.md`. Dodatkowo: polecenia z `docs/VM.md` przepisane 1:1 ze skryptów (test spójności);
NIEZWERYFIKOWANE w VirtualBox w opisie PR, jeśli nie było jak uruchomić.
