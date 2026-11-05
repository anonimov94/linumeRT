"""Wiązanie ctypes z natywnymi przyspieszeniami (`core/native/build/liblinumert_native.so`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-11-05

Biblioteka C (C11, tylko libc/libm, `make -C core/native shared`) liczy poza RT dwie pętle,
których numpy nie przyspiesza (pomiar: `docs/raporty/WYDAJNOSC_2026-11-05.md`):
- `zmap_cut` — przejazd narzędzia po mapie przygotówki (`linumert_sim.zmap.StockMap.cut`);
- `relief_heights` — wysokość frezu kulistego nad STL (`linumert.generators.relief`).

Każda funkcja ma odpowiednik w Pythonie: ścieżkę zapasową i referencyjną. Bez biblioteki
(Windows bez WSL, brak kompilatora, `LINUMERT_NATIVE=0`) wszystko działa w Pythonie, wolniej.
Biblioteki nie budujemy przy imporcie: ekran i symulacja nie uruchamiają kompilatora.
Zmienne: `LINUMERT_NATIVE=0` wyłącza bibliotekę, `LINUMERT_NATIVE_LIB` wskazuje inny plik.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import shutil
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NATIVE_DIR = ROOT / "core" / "native"
DEFAULT_LIB = NATIVE_DIR / "build" / "liblinumert_native.so"
ABI = 1                       # lrt_native.h: LRT_NATIVE_ABI
MAX_PARTS = 32
PROFILE_FLAT, PROFILE_BALL, PROFILE_BULL, PROFILE_CONE = 0, 1, 2, 3


class NativeUnavailable(RuntimeError):
    """Brak biblioteki natywnej albo niezgodna wersja ABI."""


class CCutter(ctypes.Structure):
    _fields_ = [("radius", ctypes.c_double), ("corner", ctypes.c_double),
                ("corner_sq", ctypes.c_double), ("cone_tan", ctypes.c_double),
                ("profile", ctypes.c_int32), ("reserved", ctypes.c_int32)]


class CCutResult(ctypes.Structure):
    _fields_ = [("removed", ctypes.c_double), ("contact_at", ctypes.c_double * 3),
                ("parts", ctypes.c_uint32), ("has_contact", ctypes.c_int32)]


_UNSET = object()
_state: object = _UNSET          # (biblioteka albo None, powód braku)


def build_library(build_dir: Path | None = None) -> Path:
    """`make -C core/native shared` (opcjonalnie BUILD=katalog); zwraca ścieżkę biblioteki."""
    if shutil.which("make") is None or (shutil.which("cc") is None
                                        and shutil.which("gcc") is None):
        raise NativeUnavailable("brak make i kompilatora C — zbuduj bibliotekę w Linuksie/WSL")
    cmd = ["make", "-s", "-C", str(NATIVE_DIR), "shared"]
    if build_dir is not None:
        cmd.append(f"BUILD={Path(build_dir).resolve()}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode != 0:
        raise NativeUnavailable(f"budowa biblioteki natywnej nie powiodła się:\n{result.stderr}")
    return (Path(build_dir).resolve() if build_dir is not None else DEFAULT_LIB.parent) \
        / DEFAULT_LIB.name


def load_library(path: Path | str) -> ctypes.CDLL:
    """Ładuje bibliotekę z pliku i sprawdza ABI (NativeUnavailable przy błędzie)."""
    path = Path(path)
    if not path.exists():
        raise NativeUnavailable(f"brak biblioteki {path} (make -C core/native shared)")
    try:
        lib = ctypes.CDLL(str(path))
    except OSError as error:
        raise NativeUnavailable(f"nie można załadować {path}: {error}") from error
    for symbol in ("lrt_native_abi", "lrt_zmap_cut", "lrt_relief_heights"):
        if not hasattr(lib, symbol):
            raise NativeUnavailable(f"{path}: brak wymaganego symbolu {symbol}")
    vp, i32, d = ctypes.c_void_p, ctypes.c_int32, ctypes.c_double
    lib.lrt_native_abi.argtypes, lib.lrt_native_abi.restype = [], ctypes.c_int
    if lib.lrt_native_abi() != ABI:
        raise NativeUnavailable(f"{path}: ABI {lib.lrt_native_abi()}, oczekiwano {ABI}")
    lib.lrt_zmap_cut.argtypes = [vp, i32, i32, vp, vp, d, d, d, d, ctypes.POINTER(CCutter),
                                 vp, vp, i32, d, vp, vp, i32, i32, d,
                                 ctypes.POINTER(CCutResult)]
    lib.lrt_zmap_cut.restype = ctypes.c_int
    lib.lrt_relief_heights.argtypes = [vp, ctypes.c_size_t, vp, ctypes.c_size_t, d, d, vp, vp]
    lib.lrt_relief_heights.restype = ctypes.c_int
    return lib


def library() -> ctypes.CDLL | None:
    """Biblioteka do użycia albo None (wtedy ścieżka Pythona). Wynik jest zapamiętany."""
    global _state
    if _state is _UNSET:
        if os.environ.get("LINUMERT_NATIVE", "1").strip() == "0":
            _state = (None, "wyłączona przez LINUMERT_NATIVE=0")
        else:
            try:
                _state = (load_library(os.environ.get("LINUMERT_NATIVE_LIB", DEFAULT_LIB)), "")
            except NativeUnavailable as error:
                _state = (None, str(error))
    return _state[0]  # type: ignore[index]


def available() -> bool:
    return library() is not None


def reason() -> str:
    """Dlaczego biblioteka nie jest używana (pusty tekst, gdy jest)."""
    library()
    return _state[1]  # type: ignore[index]


@contextlib.contextmanager
def override(lib: ctypes.CDLL | None, why: str = "wyłączona w teście") -> Iterator[None]:
    """Tymczasowo wymusza bibliotekę (`lib`) albo ścieżkę Pythona (`None`) — dla testów."""
    global _state
    saved = _state
    _state = (lib, "" if lib is not None else why)
    try:
        yield
    finally:
        _state = saved


def _ptr(array: np.ndarray, dtype, writeable: bool = False) -> int:
    if (array.dtype != dtype or not array.flags.c_contiguous
            or (writeable and not array.flags.writeable)):
        raise ValueError(f"tablica musi być ciągła {np.dtype(dtype).name}"
                         + (" i zapisywalna" if writeable else ""))
    return array.ctypes.data


def cutter_struct(kind: str, radius: float, corner: float, cone_tan: float) -> CCutter:
    """Profil jak `Cutter.lower`: kula/lizak, torus z narożem, stożek, inaczej płaski."""
    if kind in ("ball", "lollipop"):
        profile = PROFILE_BALL
    elif kind == "bull" and corner > 0:
        profile = PROFILE_BULL
    elif cone_tan > 0:
        profile = PROFILE_CONE
    else:
        profile = PROFILE_FLAT
    return CCutter(radius, corner, corner ** 2, cone_tan, profile, 0)


class ZmapGrid:
    """Wskaźniki mapy przygotówki dla `zmap_cut` (tablice muszą żyć dłużej niż obiekt)."""

    def __init__(self, lib: ctypes.CDLL, h: np.ndarray, xs: np.ndarray, ys: np.ndarray):
        if h.ndim != 2 or h.shape != (len(ys), len(xs)):
            raise ValueError("mapa wysokości: kształt (ny, nx) zgodny z xs, ys")
        self.lib, self.h, self.xs, self.ys = lib, h, xs, ys
        self.ptrs = (_ptr(h, np.float32, True), _ptr(xs, np.float64), _ptr(ys, np.float64))
        self.parts: dict[tuple, tuple] = {}     # tablice C części nietnących wg (r, z od)

    def valid_for(self, lib, h, xs, ys) -> bool:
        return self.lib is lib and self.h is h and self.xs is xs and self.ys is ys


def zmap_cut(grid: ZmapGrid, x0: float, y0: float, cell: float, z_bottom: float,
             cutter: CCutter, parts: Sequence[tuple[float, float]], reach: float,
             p0: Sequence[float], p1: Sequence[float], first: int, n: int, eps: float
             ) -> tuple[float, int, tuple[float, float, float] | None]:
    """(objętość [mm³], maska części w materiale, pierwszy kontakt) — jak `StockMap.cut`."""
    if len(parts) > MAX_PARTS:
        raise ValueError(f"najwyżej {MAX_PARTS} części nietnących")
    key = tuple(parts)
    arrays = grid.parts.get(key)
    if arrays is None:
        if len(grid.parts) > 64:
            grid.parts.clear()
        arrays = grid.parts[key] = (
            (ctypes.c_double * max(len(parts), 1))(*[p[0] for p in parts]),
            (ctypes.c_double * max(len(parts), 1))(*[p[1] for p in parts]))
    radii, z_from = arrays
    a = (ctypes.c_double * 3)(*p0)
    b = (ctypes.c_double * 3)(*p1)
    out = CCutResult()
    h, xs, ys = grid.ptrs
    ny, nx = grid.h.shape
    code = grid.lib.lrt_zmap_cut(h, nx, ny, xs, ys, x0, y0, cell, z_bottom,
                                 ctypes.byref(cutter), ctypes.addressof(radii),
                                 ctypes.addressof(z_from), len(parts), reach,
                                 ctypes.addressof(a), ctypes.addressof(b), first, n, eps,
                                 ctypes.byref(out))
    if code != 0:
        raise ValueError(f"lrt_zmap_cut: niepoprawne argumenty (kod {code})")
    contact = tuple(out.contact_at) if out.has_contact else None
    return out.removed, int(out.parts), contact  # type: ignore[return-value]


def relief_heights(lib: ctypes.CDLL, triangles: np.ndarray, xy: np.ndarray,
                   radius: float) -> np.ndarray:
    """`ball_tip_height` dla punktów `xy` (n, 2); -inf, gdy kula nie sięga siatki."""
    tris = np.ascontiguousarray(triangles, dtype=np.float64)
    pts = np.ascontiguousarray(xy, dtype=np.float64)
    if tris.ndim != 3 or tris.shape[1:] != (3, 3) or pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("relief_heights: trójkąty (n, 3, 3) i punkty (n, 2)")
    out = np.empty(len(pts), dtype=np.float64)
    work = np.empty(max(len(tris), 1), dtype=np.int32)
    code = lib.lrt_relief_heights(_ptr(tris, np.float64), len(tris), _ptr(pts, np.float64),
                                  len(pts), float(radius), float(radius) ** 2,
                                  _ptr(work, np.int32, True), _ptr(out, np.float64, True))
    if code != 0:
        raise ValueError(f"lrt_relief_heights: niepoprawne argumenty (kod {code})")
    return out
