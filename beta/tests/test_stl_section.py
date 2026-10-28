# SPDX-License-Identifier: GPL-2.0-or-later
"""STL fixtures are original geometry. Model-Author: Codex."""
import math
import struct

import numpy as np
import pytest

from linumert.programs.stl_section import Mesh, read_stl, section_xy


def write_cube(path, binary=True, omitted=()):
    vertices = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    faces = [f for i, f in enumerate(faces) if i not in omitted]
    if binary:
        data = b"solid binary header".ljust(80, b"\0") + struct.pack("<I", len(faces))
        for face in faces:
            data += struct.pack("<12fH", 0, 0, 0, *(n for i in face for n in vertices[i]), 0)
        path.write_bytes(data)
    else:
        lines = ["solid cube"]
        for face in faces:
            lines += ["facet normal 0 0 0", "outer loop"]
            lines += ["vertex " + " ".join(map(str, vertices[i])) for i in face]
            lines += ["endloop", "endfacet"]
        path.write_text("\n".join(lines + ["endsolid cube"]), encoding="ascii")
    return path


@pytest.mark.parametrize("binary", [True, False])
def test_cube_section_units_centering_and_order(tmp_path, binary):
    mesh = read_stl(write_cube(tmp_path / "cube.stl", binary))
    assert len(mesh.triangles) == 12 and not mesh.triangles.flags.writeable
    path, = section_xy(mesh, 0.5)
    assert path[0] == path[-1]
    area = sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(path[:-1], path[1:], strict=True)) / 2
    assert abs(area) == pytest.approx(1)
    assert section_xy(Mesh(mesh.triangles[::-1]), 0.5) == [path]
    scaled, = section_xy(mesh, 12.7, 25.4, True)
    assert min(x for x, _ in scaled) == -12.7 and max(x for x, _ in scaled) == 12.7


def test_open_mesh_and_invalid_plane_are_not_accepted(tmp_path):
    mesh = read_stl(write_cube(tmp_path / "open.stl", omitted=(4, 5)))
    with pytest.raises(ValueError, match="otwarty"):
        section_xy(mesh, 0.5)
    for plane in (0, 1, -1, math.nan):
        with pytest.raises(ValueError):
            section_xy(mesh, plane)


def test_two_shells_are_kept_as_separate_contours(tmp_path):
    mesh = read_stl(write_cube(tmp_path / "cube.stl"))
    second = mesh.triangles + [3, 0, 0]
    assert len(section_xy(Mesh(np.concatenate([mesh.triangles, second])), 0.5)) == 2


@pytest.mark.parametrize("data", [b"", b"solid\nendsolid", b"bad stl", b"\0" * 84])
def test_bad_files_are_rejected(tmp_path, data):
    path = tmp_path / "bad.stl"
    path.write_bytes(data)
    with pytest.raises(ValueError):
        read_stl(path)


def test_nonfinite_truncated_and_oversized_files(tmp_path, monkeypatch):
    path = write_cube(tmp_path / "cube.stl")
    data = bytearray(path.read_bytes())
    struct.pack_into("<f", data, 96, math.nan)
    path.write_bytes(data)
    with pytest.raises(ValueError):
        read_stl(path)
    write_cube(path)
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(ValueError):
        read_stl(path)
    write_cube(path)
    monkeypatch.setattr("linumert.programs.stl_section.MAX_BYTES", 32)
    with pytest.raises(ValueError, match="limit"):
        read_stl(path)
